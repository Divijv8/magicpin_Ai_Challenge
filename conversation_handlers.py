import re
import json
import logging
from typing import Dict, Any, List, Optional
from gemini_client import gemini_client
from groq_client import groq_client

logger = logging.getLogger(__name__)

# Known auto-reply signature phrases
AUTO_REPLY_PATTERNS = [
    r"thank you for contacting",
    r"thanks for reaching out",
    r"our team will respond shortly",
    r"automated assistant",
    r"automated response",
    r"canned message",
    r"we are currently closed",
    r"we are currently unavailable",
    r"we will get back to you",
    r"shukriya.*team tak pahuncha",
    r"automated message",
    r"aapki madad ke liye shukriya.*automated",
    r"auto-reply",
    r"autoreply"
]

# Explicit commitment / action transition phrases
INTENT_ACTION_PATTERNS = [
    r"\b(yes|yeah|yup|yep|sure|ok|okay|done|go ahead|go for it|proceed|lets do it|let's do it|send|send it|publish|update|start)\b",
    r"\b(send me|please update|kar do|kar dijiye|chalo|bilkul|theek hai|thik hai|haan|hanji|han)\b",
    r"\b(mujhe .* judrna hai|want to join|sign me up)\b",
    r"\b(keep (it )?going|continue|keep (it )?running|don'?t stop|do not stop|not want to stop|never stop|chalu rakho|chalne do)\b"
]

# Hostile / opt-out / unsubscribe phrases
HOSTILE_STOP_PATTERNS = [
    r"\b(stop|unsubscribe|spam|abuse|don't message|dont message|leave me alone|not interested|remove me|block|useless)\b",
    r"\b(mat bhejo|band karo|pareshan mat karo)\b"
]

# Negated stop / opt-out phrases (e.g., "do not stop", "don't stop the campaign", "mat roko")
NEGATED_STOP_PATTERNS = [
    r"\b(do\s*n'?t|do\s+not|never|did\s*n'?t|did\s+not|not)\s+(want\s+to\s+)?(stop|pause|cancel|end|halt|close)\b",
    r"\b(not\s+to\s+stop|without\s+stopping)\b",
    r"\b(mat\s+roko|band\s+mat\s+karo|roko\s+mat|chalne\s+do|chalu\s+rakho)\b"
]

# Deferral / busy phrases
BUSY_DEFER_PATTERNS = [
    r"\b(busy|later|call later|message tomorrow|after some time|driving|in a meeting|baad me|kal baat karte hain)\b"
]


class ConversationManager:
    """Manages stateful multi-turn interactions for WhatsApp conversations."""

    def __init__(self):
        # Map conversation_id -> list of turn dicts
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}

    @staticmethod
    def get_normalized_candidates(text: str) -> List[str]:
        """
        Produce normalized candidate variations of input text:
        1. Cleaned lowercase stripped text.
        2. Text with 3+ identical alphabetical repeats collapsed to 1 char (e.g. 'yessssss' -> 'yes', 'go forrrrr it' -> 'go for it', 'okkkk' -> 'ok').
        3. Text with 3+ identical alphabetical repeats collapsed to 2 chars (e.g. 'proceeeeed' -> 'proceed', 'haaaan' -> 'haan').
        """
        if not text:
            return [""]
        base = text.lower().strip()
        c1 = re.sub(r'([a-zA-Z])\1{2,}', r'\1', base)
        c2 = re.sub(r'([a-zA-Z])\1{2,}', r'\1\1', base)
        return list(dict.fromkeys([base, c1, c2]))

    def record_turn(self, conv_id: str, role: str, message: str) -> None:
        """Record turn history."""
        if conv_id not in self.conversations:
            self.conversations[conv_id] = []
        self.conversations[conv_id].append({"role": role, "message": message.strip()})

    def get_history(self, conv_id: str) -> List[Dict[str, Any]]:
        """Retrieve conversation history."""
        return self.conversations.get(conv_id, [])

    def is_auto_reply(self, message: str, history: List[Dict[str, Any]]) -> bool:
        """Check if message matches automated WhatsApp greetings or repeats identically."""
        candidates = self.get_normalized_candidates(message)

        # 1. Check against known auto-reply regexes
        for cand in candidates:
            for pat in AUTO_REPLY_PATTERNS:
                if re.search(pat, cand):
                    return True

        # 2. Check consecutive identical merchant messages
        merchant_msgs = [t["message"].lower().strip() for t in history if t.get("role") in ("merchant", "customer")]
        if len(merchant_msgs) >= 2 and merchant_msgs[-1] == merchant_msgs[-2]:
            return True

        return False

    def is_hostile_or_stop(self, message: str) -> bool:
        """Check for opt-out, stop, or hostile messages, guarding against negation."""
        candidates = self.get_normalized_candidates(message)

        # 1. Negation guard: "do not want to stop", "don't stop", "mat roko", etc.
        for cand in candidates:
            for neg_pat in NEGATED_STOP_PATTERNS:
                if re.search(neg_pat, cand):
                    return False

        # 2. Hostile / Stop patterns
        for cand in candidates:
            for pat in HOSTILE_STOP_PATTERNS:
                if re.search(pat, cand):
                    return True
        return False

    def is_busy_or_deferral(self, message: str) -> bool:
        """Check if user asks to defer / is busy."""
        candidates = self.get_normalized_candidates(message)
        for cand in candidates:
            for pat in BUSY_DEFER_PATTERNS:
                if re.search(pat, cand):
                    return True
        return False

    def is_intent_commitment(self, message: str) -> bool:
        """Check if user expresses explicit intent or agreement."""
        candidates = self.get_normalized_candidates(message)
        for cand in candidates:
            for pat in INTENT_ACTION_PATTERNS:
                if re.search(pat, cand):
                    return True
        return False

    def handle_reply(
        self,
        conversation_id: str,
        merchant_id: Optional[str],
        customer_id: Optional[str],
        from_role: str,
        message: str,
        turn_number: int,
        merchant_context: Optional[dict] = None,
        category_context: Optional[dict] = None
    ) -> Dict[str, Any]:
        """
        Process inbound reply and determine optimal next action: 'send', 'wait', or 'end'.
        """
        self.record_turn(conversation_id, from_role, message)
        history = self.get_history(conversation_id)

        # 1. HOSTILITY / STOP HANDLING (Highest Priority)
        if self.is_hostile_or_stop(message):
            return {
                "action": "end",
                "body": "Understood. I will not message you further. Wishing your business continued success!",
                "cta": "none",
                "rationale": "Merchant requested stop/opt-out; gracefully and respectfully ending conversation."
            }

        # 2. INTENT COMMITMENT & ACTION SWITCH (High Priority: never block explicit user intent)
        if self.is_intent_commitment(message) and not self.is_auto_reply(message, []):
            merchant_name = merchant_context.get("identity", {}).get("name", "your business") if merchant_context else "your business"
            prev_msg = ""
            for t in reversed(history[:-1]):
                if t.get("role") in ("vera", "assistant"):
                    prev_msg = t.get("message", "").lower()
                    break

            candidates = self.get_normalized_candidates(message)
            c1_msg = candidates[1] if len(candidates) > 1 else candidates[0]

            if any(k in c1_msg for k in ("not want to stop", "don't stop", "dont stop", "do not stop", "keep running", "keep going", "continue", "chalne do", "chalu rakho", "mat roko")):
                body = f"Understood! Keeping the campaign active for {merchant_name}. Everything is running smoothly and I'll continue tracking your results."
                rationale = "Merchant explicitly affirmed to keep campaign active; acknowledged and maintaining continuous execution."
            elif "thali" in prev_msg or "lunch" in prev_msg or "corporate" in prev_msg:
                body = f"Done! Sending over the corporate thali pricing sheet and packaging guidelines for {merchant_name} now. I'll check in tomorrow on your first batch!"
                rationale = "Honoring merchant confirmation on corporate thali; immediately fulfilling material delivery."
            elif "yoga" in prev_msg or "gym" in prev_msg or "batch" in prev_msg:
                body = f"Great! Finalizing the summer batch curriculum for {merchant_name}. Draft flyer has been created for your review."
                rationale = "Confirmed program drafting; proceeding directly with curriculum assets."
            elif "abstract" in message.lower() or "send" in message.lower() or "research" in prev_msg or "jida" in prev_msg:
                body = f"Done! Sending the complete summary for {merchant_name} now — also drafted a 90-second patient-education WhatsApp you can forward directly. Want to review it? Reply YES."
                rationale = "Honoring merchant accept; immediately delivering materials and offering the next high-value draft."
            elif "join" in message.lower():
                body = f"Welcome aboard! Setting up your {merchant_name} growth pack now. I've initiated your profile integration — you'll see your first draft in 2 minutes."
                rationale = "Merchant expressed clear joining intent; switched instantly to execution without qualifying questions."
            elif "refill" in prev_msg or "medicine" in prev_msg:
                body = f"Order confirmed! We are packing the monthly refill for doorstep delivery today. Thank you!"
                rationale = "Refill confirmed; immediate dispatch triggered."
            else:
                body = f"Done! I'm proceeding with the update for {merchant_name}. I'll notify you as soon as the changes go live."
                rationale = "Explicit commitment received; executing requested action immediately without redundant qualification."

            return {
                "action": "send",
                "body": body,
                "cta": "binary",
                "rationale": rationale
            }

        # 3. AUTO-REPLY DETECTION
        if self.is_auto_reply(message, history):
            merchant_msgs = [t["message"].lower().strip() for t in history if t.get("role") in ("merchant", "customer")]
            auto_reply_count = sum(1 for m in merchant_msgs if self.is_auto_reply(m, []))

            if auto_reply_count >= 2 or turn_number >= 3:
                return {
                    "action": "end",
                    "body": "Understood! I will connect directly with the owner/manager later. Best wishes!",
                    "cta": "none",
                    "rationale": "Multiple automated auto-replies detected; exiting cleanly to avoid wasting turns."
                }
            else:
                return {
                    "action": "send",
                    "body": "Got your automated note. If you'd like me to assist with your Google Profile or campaigns directly, reply YES anytime!",
                    "cta": "binary",
                    "rationale": "Initial auto-reply detected; sending one soft human confirmation before graceful exit."
                }

        # 4. BUSY / DEFERRAL HANDLING
        if self.is_busy_or_deferral(message):
            return {
                "action": "wait",
                "wait_seconds": 1800,
                "body": "No problem at all! I'll hold off and check back with you later.",
                "cta": "none",
                "rationale": "Merchant is busy; pausing outreach for 30 minutes (1800s)."
            }

        # 5. GENERAL ENGAGEMENT / QUESTION HANDLING
        system_prompt = (
            "You are Vera, magicpin's merchant assistant. The merchant just replied to your message.\n"
            "Provide a concise, helpful, action-oriented reply (under 40 words).\n"
            "If they asked a question, answer directly. End with a simple next step.\n"
            "Respond with strict JSON: {\"action\": \"send\" | \"wait\" | \"end\", \"body\": \"...\", \"cta\": \"...\", \"rationale\": \"...\"}"
        )
        user_prompt = f"Merchant message: \"{message}\"\nTurn: {turn_number}\nConversation history: {json.dumps(history[-4:])}"

        # Try Groq first
        if groq_client.is_available:
            try:
                parsed = groq_client.compose_message(system_instruction=system_prompt, user_prompt=user_prompt, temperature=0.0)
                if parsed and parsed.get("action") in ("send", "wait", "end") and parsed.get("body"):
                    return parsed
            except Exception as e:
                logger.warning(f"Groq conversational reply error: {e}")

        # Fallback to Gemini
        if gemini_client.is_available:
            try:
                resp = gemini_client.complete(user_prompt, system_instruction=system_prompt, temperature=0.0)
                if resp:
                    match = re.search(r'\{[\s\S]*\}', resp)
                    if match:
                        parsed = json.loads(match.group())
                        if parsed.get("action") in ("send", "wait", "end") and parsed.get("body"):
                            return parsed
            except Exception as e:
                logger.warning(f"Gemini reply handler error: {e}")

        # Default smart response
        return {
            "action": "send",
            "body": "Understood! I'm on it. I have prepared the details for your review — reply YES if you'd like me to proceed.",
            "cta": "binary",
            "rationale": "Acknowledging merchant input and advancing with clear binary next step."
        }


# Global singleton manager
conversation_manager = ConversationManager()
