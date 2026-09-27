"""
test_groq.py - Live Verification Script for Groq API (Layer 1 & Layer 2)
Tests API key presence, latency, Intent Layer classification, and Message Layer formulation.
"""

import os
import sys
import time
import json
from pathlib import Path

# Configure UTF-8 for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Try loading from .env if present
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and v and k not in os.environ:
                os.environ[k] = v

from groq_client import groq_client

print("=" * 65)
print("  VERA APEX — GROQ 2-LAYER API LIVE TEST & BENCHMARK")
print("=" * 65)

if not groq_client.is_available:
    print("\n❌ GROQ_API_KEY IS NOT SET IN YOUR .env FILE!")
    print("\nTo activate it:")
    print("  1. Open your .env file in the root directory")
    print("  2. Add your key: GROQ_API_KEY=gsk_your_actual_key_here")
    print("  3. Run this script again: python test_groq.py\n")
    sys.exit(1)

masked_key = groq_client.api_key[:6] + "..." + groq_client.api_key[-4:] if len(groq_client.api_key) > 10 else "***"
print(f"🔑 Groq API Key detected: {masked_key}")

# 1. Test Layer 1 (Intention Classifier)
print("\n" + "-" * 50)
print(f"  [TEST 1] Testing Layer 1: Intent Classification ({groq_client.intent_model})")
print("-" * 50)
t0 = time.time()
sample_intent = groq_client.classify_intent(
    user_message="Haan bilkul, send me the 1-page pricing sheet for lunch thali!",
    history=[{"role": "vera", "message": "Want to review the 1-page pricing sheet? Reply YES."}]
)
dt1 = (time.time() - t0) * 1000

if sample_intent:
    print(f"✅ Layer 1 Success! Latency: {dt1:.1f}ms")
    print("Intent JSON Output:")
    print(json.dumps(sample_intent, indent=2))
else:
    print("❌ Layer 1 Failed or returned None.")

# 2. Test Layer 2 (Message Formulation)
print("\n" + "-" * 50)
print(f"  [TEST 2] Testing Layer 2: Message Formulation ({groq_client.message_model})")
print("-" * 50)
system_prompt = (
    "You are Vera, magicpin's elite merchant-AI assistant for Indian local businesses.\n"
    "Respond in strict JSON: {\"body\": \"...\", \"cta\": \"binary\", \"send_as\": \"vera\", \"suppression_key\": \"k\", \"rationale\": \"...\"}"
)
user_prompt = "Compose a 40-word WhatsApp post for South Indian Cafe offering Lunch Thali @ ₹149 in Indiranagar."

t0 = time.time()
sample_msg = groq_client.compose_message(
    system_instruction=system_prompt,
    user_prompt=user_prompt,
    temperature=0.0
)
dt2 = (time.time() - t0) * 1000

if sample_msg:
    print(f"✅ Layer 2 Success! Latency: {dt2:.1f}ms")
    print("Message JSON Output:")
    print(json.dumps(sample_msg, indent=2))
else:
    print("❌ Layer 2 Failed or returned None.")

print("\n" + "=" * 65)
if sample_intent and sample_msg:
    total_pipeline_ms = dt1 + dt2
    print(f"🎉 2-LAYER PIPELINE BENCHMARK: {total_pipeline_ms:.1f}ms TOTAL LATENCY!")
    print("=" * 65)
