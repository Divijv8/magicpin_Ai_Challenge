"""
test_gemini.py - Live Verification Script for Gemini API
Tests API key presence, connectivity, available models, latency, and sample composition.
"""

import os
import sys
import time
import json
from pathlib import Path
from urllib import request as urlrequest, error as urlerror

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

api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")

print("=" * 60)
print("  VERA APEX — GEMINI API CONNECTIVITY & LIVE TEST")
print("=" * 60)

if not api_key or not api_key.strip():
    print("\n❌ GEMINI_API_KEY IS NOT SET IN THIS ENVIRONMENT!")
    print("\nTo activate it, choose ONE of these:")
    print("  1. In PowerShell:")
    print("     $env:GEMINI_API_KEY=\"AIzaSy...YourKey...\"")
    print("  2. Or create a .env file in this directory:")
    print("     GEMINI_API_KEY=AIzaSy...YourKey...")
    print("\nThen run this script again: python test_gemini.py\n")
    sys.exit(1)

masked_key = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 10 else "***"
print(f"🔑 API Key detected: {masked_key} (length: {len(api_key)})")

MODELS_TO_TEST = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]

success = False

for model in MODELS_TO_TEST:
    print(f"\n📡 Testing Model: {model}...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": "You are Vera, magicpin merchant assistant. Say hello to Dr. Meera in exactly 1 crisp sentence."}]
            }
        ],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 100
        }
    }
    
    start_t = time.time()
    try:
        req = urlrequest.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urlrequest.urlopen(req, timeout=15) as resp:
            elapsed = time.time() - start_t
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            candidates = data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts and "text" in parts[0]:
                    ans = parts[0]["text"].strip()
                    print(f"   Status: ✅ HTTP 200 OK (Latency: {elapsed:.2f}s)")
                    print(f"   Active Model: {model}")
                    print(f"   Gemini Output:\n   \"{ans}\"")
                    success = True
                    break
    except urlerror.HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else ""
        print(f"   Status: ❌ HTTP {e.code}: {e.reason}")
        try:
            err_json = json.loads(err_body)
            msg = err_json.get("error", {}).get("message", err_body)
            print(f"   Error Details: {msg}")
        except Exception:
            print(f"   Error Details: {err_body[:120]}")
    except Exception as e:
        print(f"   Status: ❌ Connection Error: {e}")

print("\n" + "=" * 60)
if success:
    print("🎉 GEMINI API IS FULLY FUNCTIONAL AND READY FOR MAGICPIN EVALUATION!")
else:
    print("⚠️ ALL TESTED MODELS FAILED. Check API key permissions and quota.")
print("=" * 60)
