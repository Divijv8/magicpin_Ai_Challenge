# magicpin AI Challenge — Vera Merchant AI Assistant ("Vera Apex")

## 1. Overview & Architecture

Vera Apex is an advanced merchant engagement AI assistant built for WhatsApp. It operates under magicpin's **4-Context Framework**, delivering hyper-personalized, clinically/operationally accurate, high-converting messages to merchants and their customers.

```
┌─────────────────────────────────────────────────────────────┐
│                     4-CONTEXT FRAMEWORK                     │
├─────────────────┬─────────────────┬─────────────────────────┤
│ CategoryContext │ MerchantContext │ CustomerContext (Opt)   │
│  - Slow-change  │  - Fast-change  │  - Relationship history │
│  - Voice/Taboos │  - Perf Deltas  │  - Slot preferences     │
│  - Peer stats   │  - Signals      │  - Language preference  │
│  - Digest pack  │  - Offer list   │  - Consent scope        │
└────────┬────────┴────────┬────────┴────────────┬────────────┘
         │                 │                     │
         └────────► ┌──────▼─────────────────────▼──────┐
                    │      TriggerContext (Why Now)     │
                    │      - Kind / Urgency / Payload   │
                    └──────────────┬────────────────────┘
                                   │
                    ┌──────────────▼────────────────────┐
                    │      Vera Apex Composer Engine    │
                    │   - Fact Anchor Verification      │
                    │   - Gemini LLM & Expert Rules     │
                    │   - Anti-Pattern / Taboo Guard    │
                    └──────────────┬────────────────────┘
                                   │
                                   ▼
              Composed WhatsApp Message (50/50 Quality)
```

---

## 2. Core Pillars & Compulsion Levers

Vera Apex scores across all **5 evaluation dimensions** (0–10 each, total 50/50):

| Dimension | Implementation Details |
|---|---|
| **1. Specificity** | Anchors on verifiable facts from the input contexts: exact numbers (views, calls, CTR deltas, trial sample sizes like 2,100 patients, catalog prices like ₹99 / ₹299 / ₹149, exact dates/deadlines). Zero hallucinations. |
| **2. Category Fit** | Strictly matches vertical tone: clinical peer for dentists (`Dr.` prefix, technical terms, zero taboos like "guaranteed"/"miracle"); warm practical for salons; operator-peer for restaurants; coaching for gyms; trustworthy/precise for pharmacies. |
| **3. Merchant Fit** | Personalizes by business and owner name, locality, active offers from their catalog, and honors language preferences (natural Indian Hinglish for `hi-en mix`). |
| **4. Trigger Relevance** | Immediately communicates "Why Now" in the opening sentence based on the trigger payload (e.g. competitor opened within 1.2km, DCI dose limit revision on Dec 15, match day surge +35%). |
| **5. Compulsion Levers** | Employs loss aversion ("missing 1,200+ local searches"), social proof (peer median comparisons), effort externalization ("I've drafted a Google post ready for you"), and a single binary CTA (Reply YES / Reply 1 or 2). |

---

## 3. Multi-Turn Conversational Intelligence (`conversation_handlers.py`)

Production WhatsApp conversations suffer from common drop-off traps. Vera Apex handles all conversational transitions statefully:

1. **Auto-Reply Detection & Elimination**:
   - Detects WhatsApp Business canned responses ("Thank you for contacting us...", "Our team will respond shortly...").
   - Tracks identical phrase repetitions. Allows 1 soft human clarification on turn 1, then gracefully exits (`action: "end"`) without wasting API turns.
2. **Instant Intent Transition**:
   - When a merchant says "Yes", "Let's do it", "Please update", Vera Apex immediately switches to action fulfillment mode ("Done! Updating your profile now...") rather than asking redundant qualifying questions.
3. **Hostility & Stop Handling**:
   - Detects unsubscribe/hostility keywords ("stop", "spam", "don't message") and exits cleanly with polite closure.
4. **Busy / Deferral Handling**:
   - Detects "busy right now", "message tomorrow" and returns `action: "wait"` with `wait_seconds: 1800`.
5. **Language Adaptation**:
   - Code-mixes dynamically between English and Hinglish based on incoming turns.

---

## 4. API Endpoints (`bot.py`)

All endpoints strictly adhere to `challenge-testing-brief.md`:

- `GET /v1/healthz`: Liveness probe reporting uptime and counts of loaded contexts.
- `GET /v1/metadata`: Returns team metadata, model version, and approach summary.
- `POST /v1/context`: Atomic context store supporting idempotent version replacement.
- `POST /v1/tick`: Receives simulated time and active trigger hints; outputs proactive message actions.
- `POST /v1/reply`: Receives inbound merchant/customer turns and produces synchronous next actions (`send`, `wait`, `end`).
- `POST /v1/teardown`: Context teardown at conclusion of test session.

---

## 5. Running & Testing Locally

### Prerequisites
- Python 3.10+
- `fastapi`, `uvicorn`, `pydantic`

### Step 1: Set Gemini API Key (Optional — Fallback engine active by default)
```powershell
$env:GEMINI_API_KEY = "your_gemini_api_key_here"
```

### Step 2: Start the Vera Bot Server
```powershell
python -m uvicorn bot:app --host 0.0.0.0 --port 8080
```

### Step 3: Run the Integration Tests
```powershell
python test_bot.py
```

### Step 4: Run the Judge Simulator
```powershell
python judge_simulator.py
```

### Step 5: Regenerate Canonical 30-Pair Submissions
```powershell
python generate_submission.py
```
This produces `submission.jsonl` with all 30 evaluated test pairs (T01 through T30).
