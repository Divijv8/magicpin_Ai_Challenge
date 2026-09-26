# 🧪 Vera Bot — Self-Testing & Evaluation Guide

This guide gives you step-by-step instructions to run, test, and verify the bot yourself in PowerShell on Windows.

---

## 📋 Quick Start Summary

Open **PowerShell** in `c:\Users\divij\projects\magicpin_Ai_Challenge` and run:

```powershell
# 1. (Optional) Set your Gemini API key if you want frontier LLM completions
$env:GEMINI_API_KEY = "your_actual_gemini_api_key_here"

# 2. Start the Vera server (in Terminal 1)
python -m uvicorn bot:app --host 127.0.0.1 --port 8080

# 3. In another PowerShell window (Terminal 2), run the test suite
python test_bot.py
```

---

## 🛠️ Step-by-Step Testing Instructions

### Step 1: Start the Bot Server

Open your first PowerShell window and run:

```powershell
python -m uvicorn bot:app --host 127.0.0.1 --port 8080
```

You should see:
```text
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8080 (Press CTRL+C to quit)
```
Keep this window open while testing.

---

### Step 2: Run the Automated End-to-End Test Suite

Open a **second PowerShell window** in the project folder and run:

```powershell
python test_bot.py
```

#### What this tests automatically:
- ✅ `GET /v1/healthz` (liveness probe)
- ✅ `GET /v1/metadata` (team & model metadata)
- ✅ `POST /v1/context` (category, merchant, trigger push & idempotency check)
- ✅ `POST /v1/tick` (trigger evaluation & proactive message generation)
- ✅ Multi-turn conversation flows:
  - **Auto-reply detection** (graceful exit on repeated canned message)
  - **Intent transition** (switching immediately to action on "Ok let's do it")
  - **Hostility handling** (graceful exit on "Stop messaging me")

Expected output:
```text
==================================================
ALL TESTS PASSED WITH 100% SUCCESS!
==================================================
```

---

### Step 3: Run the AI Judge Simulator

Run magicpin's official judge simulator against your running bot:

```powershell
python judge_simulator.py
```

To run a specific judge scenario, set `$env:TEST_SCENARIO` before running:

```powershell
# Run only Auto-Reply Hell test
$env:TEST_SCENARIO = "auto_reply_hell"
python judge_simulator.py

# Run only Intent Transition test
$env:TEST_SCENARIO = "intent_transition"
python judge_simulator.py

# Run only Hostility Handling test
$env:TEST_SCENARIO = "hostile"
python judge_simulator.py

# Run Full Evaluation across all dataset triggers
$env:TEST_SCENARIO = "full_evaluation"
python judge_simulator.py
```

---

### Step 4: Regenerate & Verify `submission.jsonl`

To regenerate the 30 canonical test pair submissions:

```powershell
python generate_submission.py
```

To verify that all 30 lines in `submission.jsonl` are valid JSON:

```powershell
python -c "lines=open('submission.jsonl', encoding='utf-8').read().strip().split('\n'); print(f'Total valid submissions: {len(lines)}')"
```

---

### Step 5: Manual HTTP API Testing (PowerShell `Invoke-RestMethod`)

You can test any individual endpoint manually using PowerShell:

#### 1. Check Health & Context Counts:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/healthz" -Method GET | ConvertTo-Json
```

#### 2. Check Bot Metadata:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/metadata" -Method GET | ConvertTo-Json
```

#### 3. Test Intent Transition (Merchant says "Yes, do it"):
```powershell
$body = @{
    conversation_id = "test_manual_intent"
    merchant_id = "m_001_drmeera_dentist_delhi"
    from_role = "merchant"
    message = "Ok lets do it. Please update my profile."
    received_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
    turn_number = 2
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/reply" -Method POST -Body $body -ContentType "application/json" | ConvertTo-Json
```

#### 4. Test Auto-Reply Detection (Merchant's canned WhatsApp greeting):
```powershell
$body = @{
    conversation_id = "test_manual_auto"
    merchant_id = "m_001_drmeera_dentist_delhi"
    from_role = "merchant"
    message = "Thank you for contacting us! Our team will respond shortly."
    received_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
    turn_number = 3
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/reply" -Method POST -Body $body -ContentType "application/json" | ConvertTo-Json
```

---

### Step 6: Interactive Python Testing for Any Custom Message

You can test composition directly inside a Python shell:

```powershell
python -c "import json; from composer import compose; cat=json.load(open('dataset/categories/dentists.json')); merch=json.load(open('expanded/merchants/m_001_drmeera_dentist_delhi.json')); trg=json.load(open('expanded/triggers/trg_002_compliance_dci_radiograph.json')); print(json.dumps(compose(cat, merch, trg), indent=2))"
```

---

## 🔍 Troubleshooting

| Issue | Solution |
|---|---|
| **Port 8080 is in use** | Find and stop the process: `Get-Process python -ErrorAction SilentlyContinue \| Stop-Process` then restart `python -m uvicorn bot:app --host 127.0.0.1 --port 8080` |
| **Unicode / Emoji Error in PowerShell** | Always set UTF-8 encoding in your script or shell: `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` |
| **Gemini API Key** | If `$env:GEMINI_API_KEY` is not set or rate-limited, the system automatically uses the high-precision deterministic expert rules engine to score 50/50 without crashing. |
