"""
groq_client.py - Ultra-Fast Groq LLM Integration Client
Provides high-throughput, low-latency completions for:
  1. Intention Layer (Fast slot/intent extraction with JSON mode)
  2. Final Message Formulation Layer (High-converting WhatsApp message generation)

Includes automatic 429 rate limit backoff, model fallback, and zero heavy dependencies.
"""

import os
import json
import time
import re
import logging
from typing import Optional, Dict, Any, List, Union
from urllib import request as urlrequest, error as urlerror

logger = logging.getLogger(__name__)

# Try loading from .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Fallback: read .env file directly if present
env_file = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_file):
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and v and k not in os.environ:
                        os.environ[k] = v
    except Exception:
        pass


class GroqClient:
    """Robust client for interacting with Groq Cloud REST API."""

    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(
        self,
        api_key: Optional[str] = None,
        intent_model: str = "openai/gpt-oss-20b",
        message_model: str = "openai/gpt-oss-120b"
    ):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self.intent_model = intent_model
        self.message_model = message_model
        
        # Candidate lists
        self.intent_models_to_try = ["openai/gpt-oss-20b", "qwen/qwen3.8-27b", "openai/gpt-oss-120b"]
        self.message_models_to_try = ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]

    @property
    def is_available(self) -> bool:
        """Returns True if a valid API key is present."""
        return bool(self.api_key and self.api_key.strip())

    def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        json_mode: bool = False,
        max_retries: int = 3
    ) -> Optional[str]:
        """
        Execute chat completion on Groq with exponential backoff on rate limits.
        """
        if not self.is_available:
            return None

        chosen_model = model or self.message_model
        
        # Prepare candidate list starting with chosen model
        fallback_list = self.intent_models_to_try if chosen_model in self.intent_models_to_try else self.message_models_to_try
        models_to_try = [chosen_model]
        for m in fallback_list:
            if m not in models_to_try:
                models_to_try.append(m)

        for model_name in models_to_try:
            for attempt in range(max_retries):
                try:
                    res = self._call_groq_api(
                        model=model_name,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        json_mode=json_mode
                    )
                    if res:
                        return res
                except urlerror.HTTPError as he:
                    # Handle 429 Rate Limit
                    if he.code == 429:
                        retry_after = 2.0 * (attempt + 1)
                        try:
                            # Try parsing Retry-After header
                            header_val = he.headers.get("retry-after")
                            if header_val:
                                retry_after = float(header_val)
                        except Exception:
                            pass
                        logger.warning(f"Groq Rate limit (429) on {model_name}. Sleeping {retry_after:.1f}s (Attempt {attempt+1}/{max_retries})...")
                        time.sleep(retry_after)
                        continue
                    elif he.code == 400 and json_mode:
                        # If Groq strict JSON grammar validation failed, retry immediately without json_mode header
                        try:
                            res = self._call_groq_api(
                                model=model_name,
                                messages=messages,
                                temperature=temperature,
                                max_tokens=max_tokens,
                                json_mode=False
                            )
                            if res:
                                return res
                        except Exception:
                            pass
                        break
                    else:
                        err_text = ""
                        try:
                            err_text = he.read().decode("utf-8")
                        except Exception:
                            pass
                        logger.warning(f"Groq HTTP Error {he.code} on {model_name}: {he} | {err_text}")
                        break  # Try next model
                except Exception as e:
                    logger.warning(f"Groq API Error on {model_name}: {e}")
                    break  # Try next model

        return None

    def _call_groq_api(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        json_mode: bool
    ) -> Optional[str]:
        """Internal REST API caller for Groq."""
        final_messages = [dict(m) for m in messages]

        if json_mode:
            # Groq/OpenAI JSON mode requires the word 'json' to appear in the prompt
            has_json_word = any("json" in m.get("content", "").lower() for m in final_messages)
            if not has_json_word and final_messages:
                final_messages[0]["content"] += "\nRespond strictly in valid JSON format."

        payload: Dict[str, Any] = {
            "model": model,
            "messages": final_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        body_bytes = json.dumps(payload).encode("utf-8")
        req = urlrequest.Request(
            self.GROQ_API_URL,
            data=body_bytes,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key.strip()}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            },
            method="POST"
        )

        resp = urlrequest.urlopen(req, timeout=12)
        raw_resp = resp.read().decode("utf-8")
        data = json.loads(raw_resp)

        choices = data.get("choices", [])
        if choices and "message" in choices[0]:
            return choices[0]["message"].get("content", "")
        return None

    # =========================================================================
    # LAYER 1: INTENTION CLASSIFIER LAYER
    # =========================================================================
    def classify_intent(
        self,
        user_message: str,
        history: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Layer 1: Fast Intent Classification & Slot Extraction.
        Runs on ultra-fast lightweight model (e.g., llama-3.1-8b-instant).
        """
        if not self.is_available:
            return None

        system_prompt = (
            "You are an ultra-fast Intent Classifier for Vera (magicpin's merchant/customer WhatsApp AI).\n"
            "Analyze the latest incoming message in the conversation and extract intent.\n\n"
            "ALLOWED INTENT CLASSES:\n"
            "- 'action_confirm': Merchant agrees, confirms, says yes, ok, publish, send, start, proceed, chalne do, haan.\n"
            "- 'stop_opt_out': Wants to stop, unsubscribe, block, hostile, not interested, don't message. NOTE: 'do not stop' or 'keep going' is NOT stop!\n"
            "- 'busy_defer': Busy right now, driving, call later, message tomorrow, baad me.\n"
            "- 'question_inquiry': Asking for clarification, pricing, schedule, ROI, how it works.\n"
            "- 'auto_reply': Generic automated WhatsApp greeting / away notice.\n"
            "- 'general_reply': Any other regular human reply.\n\n"
            "STRICT JSON OUTPUT FORMAT:\n"
            "{\n"
            '  "intent": "action_confirm" | "stop_opt_out" | "busy_defer" | "question_inquiry" | "auto_reply" | "general_reply",\n'
            '  "confidence": float (0.0 to 1.0),\n'
            '  "sentiment": "positive" | "neutral" | "negative",\n'
            '  "slots": {\n'
            '    "preferred_time": string or null,\n'
            '    "preferred_service": string or null\n'
            '  },\n'
            '  "rationale": "Brief reason for classification"\n'
            "}"
        )

        history_snippet = json.dumps(history[-3:]) if history else "[]"
        user_prompt = f"Recent History: {history_snippet}\nIncoming Message: \"{user_message}\""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        raw = self.complete(
            messages=messages,
            model=self.intent_model,
            temperature=0.0,
            max_tokens=256,
            json_mode=True
        )

        if raw:
            try:
                match = re.search(r'\{[\s\S]*\}', raw)
                if match:
                    return json.loads(match.group())
            except Exception as e:
                logger.warning(f"Error parsing intent JSON: {e}")
        return None

    # =========================================================================
    # LAYER 2: MESSAGE FORMULATION LAYER
    # =========================================================================
    def compose_message(
        self,
        system_instruction: str,
        user_prompt: str,
        temperature: float = 0.0
    ) -> Optional[Dict[str, Any]]:
        """
        Layer 2: High-converting WhatsApp Message Generation.
        Runs on deep reasoning model (e.g., llama-3.3-70b-versatile).
        """
        if not self.is_available:
            return None

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ]

        raw = self.complete(
            messages=messages,
            model=self.message_model,
            temperature=temperature,
            max_tokens=512,
            json_mode=True
        )

        if raw:
            try:
                match = re.search(r'\{[\s\S]*\}', raw)
                if match:
                    return json.loads(match.group())
            except Exception as e:
                logger.warning(f"Error parsing message JSON: {e}")
        return None


# Global singleton instance
groq_client = GroqClient()
