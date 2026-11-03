"""Ollama local models provider integration with automatic fallback to pulled models."""
import time
import requests

class OllamaProvider:
    def __init__(self, api_key='', base_url='http://localhost:11434', model_id='llama3', timeout=120):
        self.api_key = api_key
        self.base_url = (base_url or 'http://localhost:11434').rstrip('/')
        self.model_id = model_id.strip() or 'llama3'
        self.timeout = timeout

    def test_connection(self):
        url = f"{self.base_url}/api/tags"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                models = [m.get("name") for m in resp.json().get("models", [])]
                if models:
                    return {
                        "success": True,
                        "message": f"Connected to Ollama! Found {len(models)} local models: {', '.join(models[:4])}",
                        "models": models
                    }
                else:
                    return {
                        "success": True,
                        "message": "Connected to Ollama, but no models have been pulled yet. Run 'ollama pull llama3' in your terminal.",
                        "models": []
                    }
            return {"success": False, "message": f"Ollama returned status code {resp.status_code}"}
        except requests.ConnectionError:
            return {
                "success": False,
                "message": f"Cannot connect to Ollama at {self.base_url}. Make sure Ollama is installed and running."
            }
        except Exception as e:
            return {"success": False, "message": f"Connection error: {str(e)}"}

    def list_models(self):
        url = f"{self.base_url}/api/tags"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                result = []
                for m in models:
                    name = m.get("name", "")
                    caps = ["chat", "coding", "reasoning", "document", "safety"]
                    if any(v in name.lower() for v in ["llava", "vision", "moondream", "bakllava"]):
                        caps.append("vision")
                    result.append({"id": name, "name": name, "capabilities": caps})
                return result if result else self._default_models()
        except Exception:
            pass
        return self._default_models()

    def _default_models(self):
        return [
            {"id": "llama3", "name": "Llama 3", "capabilities": ["chat", "coding", "reasoning", "document", "safety"]},
            {"id": "mistral", "name": "Mistral 7B", "capabilities": ["chat", "coding", "reasoning", "document", "safety"]},
            {"id": "qwen2.5-coder", "name": "Qwen 2.5 Coder", "capabilities": ["chat", "coding", "reasoning"]},
            {"id": "phi3", "name": "Phi-3 Mini", "capabilities": ["chat", "coding", "reasoning", "safety"]}
        ]

    def get_capabilities(self):
        name = self.model_id.lower()
        caps = ["chat", "coding", "reasoning", "document", "safety"]
        if any(v in name for v in ["llava", "vision", "moondream", "bakllava"]):
            caps.append("vision")
        return caps

    def chat(self, prompt_or_messages, temperature=0.7, max_tokens=1024):
        url = f"{self.base_url}/api/chat"
        messages = []
        if isinstance(prompt_or_messages, str):
            messages = [{"role": "user", "content": prompt_or_messages}]
        elif isinstance(prompt_or_messages, list):
            messages = prompt_or_messages

        # Discover actually pulled local models to use as fallbacks
        available_models = []
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            if r.status_code == 200:
                available_models = [m.get("name") for m in r.json().get("models", [])]
        except Exception:
            pass

        target_model = self.model_id
        fallback_candidates = [target_model]
        for am in available_models:
            if am not in fallback_candidates:
                fallback_candidates.append(am)

        last_error = None
        for current_model in fallback_candidates:
            body = {
                "model": current_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }

            max_attempts = 2
            resp = None
            elapsed_ms = 0.0

            for attempt in range(max_attempts):
                start = time.time()
                try:
                    resp = requests.post(url, json=body, timeout=self.timeout)
                    elapsed_ms = (time.time() - start) * 1000
                    if resp.status_code == 200:
                        break
                    elif resp.status_code in [500, 503] and attempt < max_attempts - 1:
                        time.sleep(2)
                        continue
                    else:
                        break
                except requests.Timeout:
                    elapsed_ms = (time.time() - start) * 1000
                    if attempt < max_attempts - 1:
                        time.sleep(3)
                        continue
                    last_error = f"Ollama model '{current_model}' timed out after {self.timeout}s."
                    break
                except requests.ConnectionError:
                    raise RuntimeError(f"Cannot connect to Ollama at {self.base_url}. Ensure Ollama service is active.")
                except Exception as e:
                    last_error = f"Ollama error: {str(e)}"
                    break

            if resp is not None and resp.status_code == 200:
                data = resp.json()
                text = data.get("message", {}).get("content", "")
                return text or "Empty response returned.", elapsed_ms

            if resp is not None and resp.status_code in [404, 500, 503]:
                # 404 means model not pulled yet, try next installed model
                last_error = f"Model '{current_model}' returned {resp.status_code}. Trying next available model..."
                continue

            if resp is not None:
                raise RuntimeError(f"Ollama returned error {resp.status_code}: {resp.text[:200]}")

        raise RuntimeError(f"All Ollama models failed: {last_error}")
