import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

class GeminiManager:
    def __init__(self, model="gemini-3.8-flash"):
        # Locked strictly to 3.8 — no fallbacks
        self.model = model
        self.api_keys = self._load_keys()
        self.current_index = 0

        if not self.api_keys:
            raise ValueError("No Gemini API keys found in environment.")

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
        print(f"[GeminiManager] Key rotation: {old_idx + 1} -> {self.current_index + 1}")

    def _post(self, payload, timeout=120):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        headers = {"Content-Type": "application/json"}
        attempts = 0
        total_keys = len(self.api_keys)
        last_error = "Unknown error"

        while attempts < total_keys:
            req_url = f"{url}?key={self.current_key}"
            try:
                response = requests.post(req_url, json=payload, headers=headers, timeout=timeout)
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        text_parts = [p.get("text", "") for p in parts if "text" in p]
                        print(f"[GeminiManager] Generation successful using {self.model} (Key {self.current_index + 1})")
                        return "".join(text_parts)
                    return ""

                last_error = f"HTTP {response.status_code} on {self.model} (Key {self.current_index + 1}): {response.text}"
                print(f"[GeminiManager] {last_error}")

                if response.status_code in (429, 503):
                    time.sleep(2.0)

                self._rotate_key()
                attempts += 1

            except requests.RequestException as e:
                last_error = f"Network error on {self.model} (Key {self.current_index + 1}): {e}"
                print(f"[GeminiManager] {last_error}")
                self._rotate_key()
                attempts += 1

        raise RuntimeError(f"All keys failed on {self.model}. Details: {last_error}")

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
