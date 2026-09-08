import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

class GeminiManager:
    def __init__(self, model=None):
        # Strict descending fallback queue: 3.8 down to 3.5 (including Flash-Lite tiers)
        configured_models = [
            "gemini-3.8-flash",
            "gemini-3.8-flash-lite",
            "gemini-3.7-flash",
            "gemini-3.7-flash-lite",
            "gemini-3.6-flash",
            "gemini-3.6-flash-lite",
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite"
        ]
        
        # If an explicit model is passed, evaluate it first
        if model:
            configured_models.insert(0, model)

        self.models = list(dict.fromkeys(configured_models))
        self.api_keys = self._load_keys()
        self.current_index = 0

        if not self.api_keys:
            raise ValueError("No Gemini API keys found in .env / Render Environment")

    def _load_keys(self):
        keys = []
        i = 1
        while True:
            key = os.getenv(f"GEMINI_API_KEY_{i}")
            if key and key.strip():
                keys.append(key.strip())
                i += 1
            else:
                break
        return keys

    @property
    def current_key(self):
        return self.api_keys[self.current_index]

    def _rotate_key(self):
        old_idx = self.current_index
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        print(f"[GeminiManager] Rotated key from index {old_idx + 1} to {self.current_index + 1}")

    def _post(self, payload, timeout=120):
        headers = {"Content-Type": "application/json"}
        last_error = "Unknown error"

        # Cascade sequentially through 3.8 -> 3.8-lite -> 3.7 -> 3.7-lite -> 3.6 -> 3.6-lite -> 3.5 -> 3.5-lite
        for model_name in self.models:
            print(f"[GeminiManager] Attempting generation with model: {model_name}")
            attempts = 0
            total_keys = len(self.api_keys)

            while attempts < total_keys:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.current_key}"
                try:
                    response = requests.post(url, json=payload, headers=headers, timeout=timeout)
                    if response.status_code == 200:
                        data = response.json()
                        candidates = data.get("candidates", [])
                        if candidates and "content" in candidates[0]:
                            parts = candidates[0]["content"].get("parts", [])
                            text_parts = [p.get("text", "") for p in parts if "text" in p]
                            print(f"[GeminiManager] Success using model: {model_name} (Key {self.current_index + 1})")
                            return "".join(text_parts)
                        return ""

                    last_error = f"HTTP {response.status_code} on [{model_name}] (Key {self.current_index + 1}): {response.text}"
                    print(f"[GeminiManager] {last_error}")

                    # If model endpoint does not exist (404), step down immediately to the next model
                    if response.status_code == 404:
                        print(f"[GeminiManager] Model '{model_name}' not found. Cascading to next model...")
                        break

                    # If rate-limited or transient service error, rotate key and pause briefly
                    if response.status_code in (400, 429, 503):
                        self._rotate_key()
                        time.sleep(1.0)
                    else:
                        self._rotate_key()

                    attempts += 1
                except requests.RequestException as e:
                    last_error = f"Network error on [{model_name}] (Key {self.current_index + 1}): {e}"
                    print(f"[GeminiManager] {last_error}")
                    self._rotate_key()
                    attempts += 1

        raise RuntimeError(f"All models (3.8 down to 3.5-lite) and keys failed. Last error: {last_error}")

    def generate_content(self, prompt, system_instruction=None, enable_search=True, timeout=120):
        payload = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ]
        }

        if enable_search:
            payload["tools"] = [{"googleSearch": {}}]

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        return self._post(payload, timeout=timeout)

    def generate_with_image(self, prompt, image_bytes, mime_type="image/jpeg", system_instruction=None, timeout=120):
        import base64
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": encoded_image
                            }
                        }
                    ]
                }
            ]
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        return self._post(payload, timeout=timeout)
