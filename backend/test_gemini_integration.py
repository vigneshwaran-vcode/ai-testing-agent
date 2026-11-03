"""Integration test for GeminiProvider using gemini-3.8-flash and available models."""
import os
import sys

backend_dir = os.path.dirname(__file__)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import get_setting
from models.gemini_provider import GeminiProvider

def test_gemini():
    api_key = get_setting("GOOGLE_API_KEY", "")
    print(f"1. Retrieved API Key: {'***' + api_key[-4:] if api_key else 'NONE'}")
    assert api_key, "Google API Key is missing from settings!"

    # 1. Test Provider initialization with gemini-3.8-flash
    provider = GeminiProvider(api_key=api_key, model_id="gemini-3.8-flash")
    print(f"2. Provider initialized: Model={provider.model_id}")

    # 2. Test Connection
    print("3. Testing connection to Gemini API...")
    conn_result = provider.test_connection()
    print("   Connection Result:", conn_result.get("message"))
    assert conn_result["success"] is True, f"Connection test failed: {conn_result.get('message')}"
    assert "gemini-3.8-flash" in conn_result.get("models", []), "gemini-3.8-flash not found in API models list!"

    # 3. Test Capabilities
    caps = provider.get_capabilities()
    print("4. Capabilities detected for gemini-3.8-flash:", caps)
    assert "chat" in caps and "coding" in caps and "vision" in caps, "Capabilities incomplete!"

    # 4. Test Error Handling for Deprecated Model (gemini-2.0-flash)
    print("5. Testing error handling for deprecated model (gemini-2.0-flash)...")
    bad_provider = GeminiProvider(api_key=api_key, model_id="gemini-2.0-flash")
    try:
        bad_provider.chat("Hello")
        print("   [FAIL] Should have raised error for deprecated model!")
    except RuntimeError as e:
        print(f"   [PASS] Correctly caught error: {str(e)[:120]}...")
        assert "404" in str(e) or "gemini-3.8-flash" in str(e), "Error message should mention 404 or gemini-3.8-flash"

    # 5. Test Error Handling for Invalid API Key
    print("6. Testing error handling for invalid API key...")
    invalid_key_provider = GeminiProvider(api_key="AIzaSyInvalidKeyFakeTest123", model_id="gemini-3.8-flash")
    test_res = invalid_key_provider.test_connection()
    print("   Invalid key test_connection response:", test_res)
    assert test_res["success"] is False, "Invalid API key should fail connection test!"

    # 6. Test Live Chat with stable Gemini model
    print("7. Testing live chat with Gemini model (gemini-2.5-flash)...")
    chat_provider = GeminiProvider(api_key=api_key, model_id="gemini-2.5-flash", timeout=20)
    text, elapsed_ms = chat_provider.chat("What is the capital of Australia? Answer in one word.", temperature=0.7)
    print(f"   Model Response: '{text.strip()}' (took {elapsed_ms:.1f}ms)")
    assert "Canberra" in text, f"Expected 'Canberra' in response, got: {text}"

    print("\n[SUCCESS] All Gemini integration tests passed successfully!")

if __name__ == '__main__':
    test_gemini()
