"""
gemini_client.py - Gemini LLM Integration Client
Provides deterministic, structured completions using Gemini models with fallback handling.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
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


class GeminiClient:
    """Robust client for interacting with Gemini API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-3.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
        self.preferred_models = [
            model,
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-2.5-flash",
            "gemini-3.8-flash",
            "gemini-flash-latest",
        ]
        # Remove duplicates while preserving order
        seen = set()
        self.models_to_try = [m for m in self.preferred_models if not (m in seen or seen.add(m))]
        self.active_model = self.models_to_try[0]

    @property
    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def complete(self, prompt: str, system_instruction: Optional[str] = None, temperature: float = 0.0) -> Optional[str]:
        """Generate content from Gemini model with deterministic parameters."""
        if not self.is_available:
            return None

        for model_name in self.models_to_try:
            try:
                result = self._call_gemini_api(model_name, prompt, system_instruction, temperature)
                if result:
                    self.active_model = model_name
                    return result
            except Exception as e:
                logger.warning(f"Failed calling Gemini model {model_name}: {e}")
                continue

        return None

    def _call_gemini_api(self, model: str, prompt: str, system_instruction: Optional[str], temperature: float) -> Optional[str]:
        """Perform HTTP call to Google Gemini REST API."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"

        body_dict: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 2048,
                "topP": 0.95,
            }
        }

        if system_instruction:
            body_dict["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        body_bytes = json.dumps(body_dict).encode("utf-8")
        req = urlrequest.Request(
            url,
            data=body_bytes,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        resp = urlrequest.urlopen(req, timeout=10)
        raw_resp = resp.read().decode("utf-8")
        data = json.loads(raw_resp)

        candidates = data.get("candidates", [])
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            if parts and "text" in parts[0]:
                return parts[0]["text"]
        return None


# Global singleton instance
gemini_client = GeminiClient()
