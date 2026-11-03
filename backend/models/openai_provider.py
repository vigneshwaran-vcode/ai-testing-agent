"""OpenAI provider integration with resilience, retry, and model fallback."""
import time
import requests
import json

OPENAI_MODELS = [
    {"id": "gpt-4o", "name": "GPT-4o (Omni - Recommended)", "capabilities": ["chat", "coding", "reasoning", "vision", "document", "safety"]},
    {"id": "gpt-4o-mini", "name": "GPT-4o Mini (Fast & Cost-Effective)", "capabilities": ["chat", "coding", "reasoning", "vision", "document", "safety"]},
    {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "capabilities": ["chat", "coding", "reasoning", "vision", "document", "safety"]},
    {"id": "o1-preview", "name": "OpenAI o1 Preview (Advanced Reasoning)", "capabilities": ["chat", "coding", "reasoning"]},
    {"id": "o1-mini", "name": "OpenAI o1 Mini", "capabilities": ["chat", "coding", "reasoning"]},
    {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo (Legacy)", "capabilities": ["chat", "coding", "reasoning", "document", "safety"]},
    {"id": "dall-e-3", "name": "DALL-E 3", "capabilities": ["image_generation"]},
]

class OpenAIProvider:
    def __init__(self, api_key='', base_url='', model_id='gpt-4o', timeout=60):
        self.api_key = api_key.strip()
        self.base_url = (base_url or 'https://api.openai.com/v1').rstrip('/')
        self.model_id = model_id.strip() or 'gpt-4o'
        self.timeout = timeout

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def test_connection(self):
        if not self.api_key:
            return {"success": False, "message": "API key is required for OpenAI."}
        try:
            url = f"{self.base_url}/models"
            resp = requests.get(url, headers=self._headers(), timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("id") for m in data.get("data", [])]
                return {
                    "success": True,
                    "message": f"Successfully connected to OpenAI API! {len(models)} models available.",
                    "models": models
                }
            elif resp.status_code in [401, 403]:
                return {"success": False, "message": "Invalid OpenAI API key or unauthorized."}
            else:
                err = resp.json().get("error", {}).get("message", resp.text)
                return {"success": False, "message": f"OpenAI error ({resp.status_code}): {err}"}
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {str(e)}"}

    def list_models(self):
        if not self.api_key:
            return OPENAI_MODELS
        try:
            url = f"{self.base_url}/models"
            resp = requests.get(url, headers=self._headers(), timeout=8)
            if resp.status_code == 200:
                available = {m.get("id") for m in resp.json().get("data", [])}
                filtered = [m for m in OPENAI_MODELS if m["id"] in available]
                return filtered if filtered else OPENAI_MODELS
        except Exception:
            pass
        return OPENAI_MODELS

    def get_capabilities(self):
        for m in OPENAI_MODELS:
            if m["id"] == self.model_id:
                return m["capabilities"]
        return ["chat", "coding", "reasoning", "vision", "document", "safety"]

    def chat(self, prompt_or_messages, temperature=0.7, max_tokens=1024):
        if not self.api_key:
            raise ValueError("OpenAI API key is missing. Please configure it in Settings or Model Selection.")

        messages = []
        if isinstance(prompt_or_messages, str):
            messages = [{"role": "user", "content": prompt_or_messages}]
        elif isinstance(prompt_or_messages, list):
            messages = prompt_or_messages

        # Build candidate fallback list
        target_model = self.model_id
        fallback_candidates = [target_model]
        for alt in ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]:
            if alt not in fallback_candidates:
                fallback_candidates.append(alt)

        last_error = None
        for current_model in fallback_candidates:
            url = f"{self.base_url}/chat/completions"
            body = {
                "model": current_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            max_attempts = 2
            resp = None
            elapsed_ms = 0.0

            for attempt in range(max_attempts):
                start = time.time()
                try:
                    resp = requests.post(url, json=body, headers=self._headers(), timeout=self.timeout)
                    elapsed_ms = (time.time() - start) * 1000
                    if resp.status_code == 200:
                        break
                    elif resp.status_code in [429, 500, 502, 503, 504] and attempt < max_attempts - 1:
                        time.sleep(2)
                        continue
                    else:
                        break
                except requests.Timeout:
                    elapsed_ms = (time.time() - start) * 1000
                    if attempt < max_attempts - 1:
                        time.sleep(3)
                        continue
                    last_error = f"Model '{current_model}' timed out after {self.timeout}s."
                    break
                except requests.RequestException as e:
                    last_error = f"Network error: {str(e)}"
                    break

            if resp is not None and resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if not choices:
                    return "No output produced.", elapsed_ms
                text = choices[0].get("message", {}).get("content", "")
                return text or "Empty response returned.", elapsed_ms

            # If rate limited (429) or server unavailable (500-504), failover to next model
            if resp is not None and resp.status_code in [429, 500, 502, 503, 504]:
                err_msg = ""
                try:
                    err_msg = resp.json().get("error", {}).get("message", resp.text)
                except Exception:
                    err_msg = resp.text
                last_error = f"Model '{current_model}' returned {resp.status_code} ({err_msg}). Trying fallback..."
                continue

            # Non-retryable error (e.g. 401 invalid key, 400 bad request)
            if resp is not None and resp.status_code not in [200, 429, 500, 502, 503, 504]:
                err_msg = ""
                try:
                    err_msg = resp.json().get("error", {}).get("message", resp.text)
                except Exception:
                    err_msg = resp.text
                raise RuntimeError(f"OpenAI error ({resp.status_code}): {err_msg}")

        raise RuntimeError(f"All OpenAI model requests failed: {last_error}")

    def generate_image(self, prompt, size="1024x1024", quality="standard"):
        url = f"{self.base_url}/images/generations"
        body = {
            "model": "dall-e-3",
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "n": 1
        }
        start = time.time()
        resp = requests.post(url, json=body, headers=self._headers(), timeout=self.timeout)
        elapsed_ms = (time.time() - start) * 1000
        if resp.status_code != 200:
            err = resp.json().get("error", {}).get("message", resp.text)
            raise RuntimeError(f"DALL-E error ({resp.status_code}): {err}")
        data = resp.json()
        return data["data"][0]["url"], elapsed_ms
