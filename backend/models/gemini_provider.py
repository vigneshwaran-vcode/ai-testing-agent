"""Google Gemini provider integration using REST API."""
import time
import requests

GEMINI_MODELS = [
    {"id": "gemini-3.5-flash", "name": "Gemini 3.5 Flash (Recommended - Fast & Active)", "capabilities": ["chat", "coding", "reasoning", "vision", "document", "audio", "safety"]},
    {"id": "gemini-3.5-flash-lite", "name": "Gemini 3.5 Flash Lite (Ultra Fast)", "capabilities": ["chat", "coding", "reasoning", "vision", "document", "audio", "safety"]},
    {"id": "gemini-3-flash-preview", "name": "Gemini 3 Flash Preview", "capabilities": ["chat", "coding", "reasoning", "vision", "document", "audio", "safety"]},
    {"id": "gemini-3.8-flash", "name": "Gemini 3.8 Flash (High Demand)", "capabilities": ["chat", "coding", "reasoning", "vision", "document", "audio", "safety"]},
    {"id": "imagen-3.0-generate-002", "name": "Imagen 3", "capabilities": ["image_generation"]},
]

class GeminiProvider:
    def __init__(self, api_key='', base_url='', model_id='gemini-3.5-flash', timeout=60):
        self.api_key = api_key.strip()
        self.base_url = (base_url or 'https://generativelanguage.googleapis.com').rstrip('/')
        self.model_id = model_id.strip() or 'gemini-3.5-flash'
        self.timeout = timeout

    def test_connection(self):
        if not self.api_key:
            return {"success": False, "message": "API key is required for Google Gemini."}
        
        # Step 1: Query models list
        list_url = f"{self.base_url}/v1beta/models?key={self.api_key}"
        models = []
        try:
            resp = requests.get(list_url, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "").replace("models/", "") for m in data.get("models", [])]
            elif resp.status_code in [400, 401]:
                return {"success": False, "message": "Invalid Gemini API key. Please check your key at https://aistudio.google.com/app/apikey"}
            elif resp.status_code == 403:
                err_msg = resp.json().get("error", {}).get("message", resp.text)
                return {"success": False, "message": f"Gemini API 403 Permission Denied: {err_msg}"}
        except requests.Timeout:
            return {"success": False, "message": "Connection to Gemini API timed out after 12 seconds."}
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {str(e)}"}

        # Step 2: Validate live generation capability
        clean_target = self.model_id.replace("models/", "")
        gen_url = f"{self.base_url}/v1beta/models/{clean_target}:generateContent?key={self.api_key}"
        test_payload = {
            "contents": [{"parts": [{"text": "ping"}]}],
            "generationConfig": {"maxOutputTokens": 2}
        }

        try:
            gen_resp = requests.post(gen_url, json=test_payload, headers={"Content-Type": "application/json"}, timeout=12)
            if gen_resp.status_code == 200:
                return {
                    "success": True,
                    "message": f"Successfully connected! Verified live generation on model '{clean_target}'. Found {len(models)} accessible models.",
                    "models": models
                }
            else:
                err_data = gen_resp.json().get("error", {})
                err_msg = err_data.get("message", gen_resp.text)

                if "free tier is not available" in err_msg.lower():
                    return {
                        "success": False,
                        "message": (
                            "Gemini API 403 Error: The free tier is not enabled for the Google Cloud project of this API key.<br><br>"
                            "<strong>How to fix:</strong><br>"
                            "1. <strong>Free Fix:</strong> Go to <a href='https://aistudio.google.com/app/apikey' target='_blank'>Google AI Studio API Keys</a>, click <strong>'Create API key'</strong> &rarr; <strong>'Create key in new project'</strong> (free tier enabled by default).<br>"
                            "2. <strong>Billing Fix:</strong> Or enable billing for this project at <a href='https://aistudio.google.com/billing' target='_blank'>AI Studio Billing</a>."
                        ),
                        "models": models
                    }
                elif gen_resp.status_code == 404:
                    return {
                        "success": False,
                        "message": f"Model '{clean_target}' returned 404 Not Found. Please select 'gemini-3.8-flash' or another available model.",
                        "models": models
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Gemini API generation error ({gen_resp.status_code}): {err_msg}",
                        "models": models
                    }
        except requests.Timeout:
            # If generation timed out but list models worked, inform user
            return {
                "success": True,
                "message": f"Connected to Gemini API ({len(models)} models found), but ping test to '{clean_target}' took longer than 12s. Model may be high demand.",
                "models": models
            }
        except Exception as e:
            return {"success": False, "message": f"Generation check error: {str(e)}", "models": models}

    def list_models(self):
        if not self.api_key:
            return GEMINI_MODELS
        url = f"{self.base_url}/v1beta/models?key={self.api_key}"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                ret = []
                for m in data.get("models", []):
                    mid = m.get("name", "").replace("models/", "")
                    if "generateContent" in m.get("supportedGenerationMethods", []):
                        caps = ["chat", "coding", "reasoning", "document", "safety"]
                        if any(k in mid for k in ["vision", "1.5", "2.0", "2.5", "3.", "3.8"]):
                            caps.extend(["vision", "audio"])
                        ret.append({
                            "id": mid,
                            "name": m.get("displayName", mid),
                            "capabilities": caps
                        })
                return ret if ret else GEMINI_MODELS
        except Exception:
            pass
        return GEMINI_MODELS

    def get_capabilities(self):
        for m in GEMINI_MODELS:
            if m["id"] == self.model_id:
                return m["capabilities"]
        return ["chat", "coding", "reasoning", "vision", "document", "audio", "safety"]

    def chat(self, prompt_or_messages, temperature=0.7, max_tokens=1024):
        if not self.api_key:
            raise ValueError("Google Gemini API key is missing. Please configure it in Settings or Model Selection.")

        clean_model = self.model_id.replace("models/", "")

        contents = []
        if isinstance(prompt_or_messages, str):
            contents = [{"parts": [{"text": prompt_or_messages}]}]
        elif isinstance(prompt_or_messages, list):
            for m in prompt_or_messages:
                role = "user" if m.get("role") in ["user", "system"] else "model"
                contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})

        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }

        # List of candidate models to try: target model first, then healthy fallbacks
        fallback_candidates = [clean_model]
        for alt in ["gemini-3.5-flash", "gemini-3-flash-preview", "gemini-3.6-flash"]:
            if alt not in fallback_candidates:
                fallback_candidates.append(alt)

        last_error = None
        for current_model in fallback_candidates:
            url = f"{self.base_url}/v1beta/models/{current_model}:generateContent?key={self.api_key}"
            resp = None
            elapsed_ms = 0.0
            max_attempts = 2

            for attempt in range(max_attempts):
                start = time.time()
                try:
                    resp = requests.post(
                        url,
                        json=body,
                        headers={"Content-Type": "application/json"},
                        timeout=self.timeout
                    )
                    elapsed_ms = (time.time() - start) * 1000
                    if resp.status_code == 200:
                        break
                    elif resp.status_code in [503, 429] and attempt < max_attempts - 1:
                        time.sleep(2)
                        continue
                    else:
                        break
                except requests.Timeout:
                    elapsed_ms = (time.time() - start) * 1000
                    if attempt < max_attempts - 1:
                        time.sleep(3)
                        continue
                    last_error = f"Request timed out for model '{current_model}' after {self.timeout}s."
                    break
                except requests.RequestException as e:
                    last_error = f"Network error communicating with Gemini API: {str(e)}"
                    break

            if resp is not None and resp.status_code == 200:
                # Successfully generated response!
                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    prompt_feedback = data.get("promptFeedback", {})
                    block_reason = prompt_feedback.get("blockReason")
                    if block_reason:
                        return f"Model response blocked by safety filter: {block_reason}", elapsed_ms
                    return "No response generated by model.", elapsed_ms

                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts if "text" in p)
                if not text and parts:
                    text = str(parts[0].get("text", ""))

                return text or "Empty response returned by model.", elapsed_ms

            # If 503 or 429, try the next fallback model in the list
            if resp is not None and resp.status_code in [503, 429]:
                err_msg = ""
                try:
                    err_msg = resp.json().get("error", {}).get("message", resp.text)
                except Exception:
                    err_msg = resp.text
                last_error = f"Model '{current_model}' returned {resp.status_code} ({err_msg}). Trying fallback..."
                continue

            # For non-retryable errors (e.g. 400, 401, 403), raise immediately
            if resp is not None and resp.status_code not in [200, 503, 429]:
                try:
                    err_json = resp.json().get("error", {})
                    err_msg = err_json.get("message", resp.text)
                except Exception:
                    err_msg = resp.text

                if "free tier is not available" in err_msg.lower():
                    raise RuntimeError(
                        "Gemini API 403 Error: The free tier is not enabled for the Google Cloud project of this API key."
                    )
                elif resp.status_code in [400, 401, 403]:
                    raise RuntimeError(f"Gemini API authentication error ({resp.status_code}): {err_msg}")
                else:
                    raise RuntimeError(f"Gemini API returned error {resp.status_code}: {err_msg}")

        raise RuntimeError(f"All Gemini models failed to respond: {last_error}")
