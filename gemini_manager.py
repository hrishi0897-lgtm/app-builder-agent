import os
import requests
from dotenv import load_dotenv

load_dotenv()

class GeminiManager:
    def __init__(self, model="gemini-2.5-flash"):
        self.model = model
        self.api_keys = self._load_keys()
        self.current_index = 0

        if not self.api_keys:
            raise ValueError("No Gemini API keys found in .env")

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

    def _post(self, payload, timeout=90):
        url_template = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        headers = {"Content-Type": "application/json"}
        attempts = 0
        total_keys = len(self.api_keys)

        while attempts < total_keys:
            url = f"{url_template}?key={self.current_key}"
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=timeout)
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        text_parts = [p.get("text", "") for p in parts if "text" in p]
                        return "".join(text_parts)
                    return ""
                elif response.status_code in (429, 503):
                    print(f"[GeminiManager] Key {self.current_index + 1} hit rate limit / service error (HTTP {response.status_code}).")
                    self._rotate_key()
                    attempts += 1
                else:
                    raise RuntimeError(f"Gemini API error {response.status_code}: {response.text}")
            except requests.RequestException as e:
                print(f"[GeminiManager] Request failed on key {self.current_index + 1}: {e}")
                self._rotate_key()
                attempts += 1

        raise RuntimeError("All Gemini API keys exhausted or rate-limited.")

    def generate_content(self, prompt, system_instruction=None, enable_search=True, timeout=90):
        payload = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ]
        }

        # Google Search Grounding for live web research
        if enable_search:
            payload["tools"] = [{"googleSearch": {}}]

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        return self._post(payload, timeout=timeout)

    def generate_with_image(self, prompt, image_bytes, mime_type="image/jpeg", system_instruction=None, timeout=90):
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
