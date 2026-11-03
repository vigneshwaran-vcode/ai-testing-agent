"""Custom OpenAI-compatible API endpoint provider with retry and error handling."""
import time
import requests

class CustomProvider:
    def __init__(self, api_key='', base_url='', model_id='custom-model', timeout=60):
        self.api_key = api_key.strip()
        self.base_url = (base_url or 'http://localhost:8000/v1').rstrip('/')
        self.model_id = model_id.strip() or 'custom-model'
        self.timeout = timeout

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def test_connection(self):
        if not self.base_url:
            return {"success": False, "message": "Custom API endpoint URL is required."}
        try:
            url = f"{self.base_url}/models"
            resp = requests.get(url, headers=self._headers(), timeout=8)
            if resp.status_code == 200:
                models = [m.get("id") for m in resp.json().get("data", [])]
                return {
                    "success": True,
                    "message": f"Successfully connected to Custom API endpoint! Found {len(models)} models.",
                    "models": models
                }
        except Exception:
            pass

        try:
            url = f"{self.base_url}/chat/completions"
            body = {
                "model": self.model_id,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5
            }
            resp = requests.post(url, json=body, headers=self._headers(), timeout=10)
            if resp.status_code == 200:
                return {"success": True, "message": f"Connected to custom endpoint at {self.base_url} successfully."}
            else:
                return {"success": False, "message": f"Endpoint responded with error {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": f"Could not connect to {self.base_url}: {str(e)}"}

    def list_models(self):
        try:
            url = f"{self.base_url}/models"
            resp = requests.get(url, headers=self._headers(), timeout=6)
            if resp.status_code == 200:
                return [{"id": m.get("id"), "name": m.get("id"), "capabilities": ["chat", "coding", "reasoning", "document", "safety"]}
                        for m in resp.json().get("data", [])]
        except Exception:
            pass
        return [{"id": self.model_id, "name": self.model_id, "capabilities": ["chat", "coding", "reasoning", "document", "safety"]}]

    def get_capabilities(self):
        return ["chat", "coding", "reasoning", "document", "safety"]

    def chat(self, prompt_or_messages, temperature=0.7, max_tokens=1024):
        url = f"{self.base_url}/chat/completions"
        messages = []
        if isinstance(prompt_or_messages, str):
            messages = [{"role": "user", "content": prompt_or_messages}]
        elif isinstance(prompt_or_messages, list):
            messages = prompt_or_messages

        body = {
            "model": self.model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        max_attempts = 2
        last_error = None
        for attempt in range(max_attempts):
            start = time.time()
            try:
                resp = requests.post(url, json=body, headers=self._headers(), timeout=self.timeout)
                elapsed_ms = (time.time() - start) * 1000
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if not choices:
                        return "No output produced.", elapsed_ms
                    return choices[0].get("message", {}).get("content", "") or "Empty response returned.", elapsed_ms
                elif resp.status_code in [429, 502, 503, 504] and attempt < max_attempts - 1:
                    time.sleep(2)
                    continue
                else:
                    raise RuntimeError(f"Custom API error ({resp.status_code}): {resp.text[:250]}")
            except requests.Timeout:
                if attempt < max_attempts - 1:
                    time.sleep(3)
                    continue
                raise RuntimeError(f"Custom endpoint at {self.base_url} timed out after {self.timeout}s.")
            except requests.RequestException as e:
                raise RuntimeError(f"Custom API network error: {str(e)}")

        raise RuntimeError(f"Custom endpoint request failed: {last_error}")
