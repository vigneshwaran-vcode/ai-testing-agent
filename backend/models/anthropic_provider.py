"""Anthropic Claude provider integration using REST API with resilience, retry, and model fallback."""
import time
import requests

ANTHROPIC_MODELS = [
    {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet (Recommended)", "capabilities": ["chat", "coding", "reasoning", "vision", "document", "safety"]},
    {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku (Ultra Fast)", "capabilities": ["chat", "coding", "reasoning", "document", "safety"]},
    {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "capabilities": ["chat", "coding", "reasoning", "vision", "document", "safety"]},
    {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet", "capabilities": ["chat", "coding", "reasoning", "vision", "document", "safety"]},
    {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku", "capabilities": ["chat", "coding", "reasoning", "vision", "document", "safety"]},
]

class AnthropicProvider:
    def __init__(self, api_key='', base_url='', model_id='claude-3-5-sonnet-20241022', timeout=60):
        self.api_key = api_key.strip()
        self.base_url = (base_url or 'https://api.anthropic.com').rstrip('/')
        self.model_id = model_id.strip() or 'claude-3-5-sonnet-20241022'
        self.timeout = timeout

    def _headers(self):
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

    def test_connection(self):
        if not self.api_key:
            return {"success": False, "message": "API key is required for Anthropic Claude."}
        url = f"{self.base_url}/v1/messages"
        body = {
            "model": self.model_id,
            "max_tokens": 10,
            "messages": [{"role": "user", "content": "ping"}]
        }
        try:
            resp = requests.post(url, json=body, headers=self._headers(), timeout=12)
            if resp.status_code == 200:
                return {"success": True, "message": f"Successfully connected to Anthropic API using model '{self.model_id}'."}
            elif resp.status_code in [401, 403]:
                return {"success": False, "message": "Invalid Anthropic API key or unauthorized."}
            else:
                err = resp.json().get("error", {}).get("message", resp.text)
                return {"success": False, "message": f"Anthropic error ({resp.status_code}): {err}"}
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {str(e)}"}

    def list_models(self):
        return ANTHROPIC_MODELS

    def get_capabilities(self):
        for m in ANTHROPIC_MODELS:
            if m["id"] == self.model_id:
                return m["capabilities"]
        return ["chat", "coding", "reasoning", "document", "safety"]

    def chat(self, prompt_or_messages, temperature=0.7, max_tokens=1024):
        if not self.api_key:
            raise ValueError("Anthropic API key is missing. Please configure it in Settings or Model Selection.")

        messages = []
        system_prompt = None

        if isinstance(prompt_or_messages, str):
            messages = [{"role": "user", "content": prompt_or_messages}]
        elif isinstance(prompt_or_messages, list):
            for m in prompt_or_messages:
                if m.get("role") == "system":
                    system_prompt = m.get("content", "")
                else:
                    messages.append({"role": m.get("role", "user"), "content": m.get("content", "")})

        # Fallback candidate list: requested model first, then haiku/sonnet
        target_model = self.model_id
        fallback_candidates = [target_model]
        for alt in ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-haiku-20240307"]:
            if alt not in fallback_candidates:
                fallback_candidates.append(alt)

        last_error = None
        for current_model in fallback_candidates:
            url = f"{self.base_url}/v1/messages"
            body = {
                "model": current_model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages
            }
            if system_prompt:
                body["system"] = system_prompt

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
                    elif resp.status_code in [429, 529, 500, 503] and attempt < max_attempts - 1:
                        time.sleep(2)
                        continue
                    else:
                        break
                except requests.Timeout:
                    elapsed_ms = (time.time() - start) * 1000
                    if attempt < max_attempts - 1:
                        time.sleep(3)
                        continue
                    last_error = f"Claude model '{current_model}' timed out after {self.timeout}s."
                    break
                except requests.RequestException as e:
                    last_error = f"Network error: {str(e)}"
                    break

            if resp is not None and resp.status_code == 200:
                data = resp.json()
                content_blocks = data.get("content", [])
                text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
                return text or "Empty response returned.", elapsed_ms

            # 429 (rate limit) or 529 (overloaded) -> try fallback model
            if resp is not None and resp.status_code in [429, 529, 500, 503]:
                err_msg = ""
                try:
                    err_msg = resp.json().get("error", {}).get("message", resp.text)
                except Exception:
                    err_msg = resp.text
                last_error = f"Model '{current_model}' returned {resp.status_code} ({err_msg}). Trying fallback..."
                continue

            # Non-retryable error
            if resp is not None and resp.status_code not in [200, 429, 529, 500, 503]:
                err_msg = ""
                try:
                    err_msg = resp.json().get("error", {}).get("message", resp.text)
                except Exception:
                    err_msg = resp.text
                raise RuntimeError(f"Anthropic error ({resp.status_code}): {err_msg}")

        raise RuntimeError(f"All Anthropic models failed: {last_error}")
