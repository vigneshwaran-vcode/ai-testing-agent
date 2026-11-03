"""AI Model Capability Detection based on provider, model ID, and integration."""

CAPABILITY_DEFINITIONS = {
    "chat": {
        "id": "chat",
        "name": "Chatbot & Conversation",
        "icon": "bi-chat-dots-fill",
        "color": "primary",
        "description": "Examines conversational QA, instruction following, context retention, ambiguity handling, and multi-turn consistency.",
        "subcategories": [
            "General Question Answering",
            "Multi-turn Dialogue",
            "Context Retention",
            "Strict Instruction Following",
            "Ambiguity & Clarification",
            "Consistency Across Turns"
        ]
    },
    "coding": {
        "id": "coding",
        "name": "Coding & Programming",
        "icon": "bi-code-slash",
        "color": "success",
        "description": "Tests code generation, bug fixing, algorithmic correctness, and runs generated code in a safe sandbox.",
        "subcategories": [
            "Algorithm Implementation",
            "Bug Identification & Fixing",
            "Code Explanation",
            "Unit Test Writing",
            "Code Execution Correctness"
        ]
    },
    "reasoning": {
        "id": "reasoning",
        "name": "Reasoning & Problem-Solving",
        "icon": "bi-cpu-fill",
        "color": "warning",
        "description": "Evaluates logical deductions, mathematical problem-solving, multi-step logic, and contradiction detection.",
        "subcategories": [
            "Logical Deduction",
            "Mathematical Problem Solving",
            "Multi-step Planning",
            "Contradiction Identification",
            "Justified Conclusions"
        ]
    },
    "document": {
        "id": "document",
        "name": "Document & Text Processing",
        "icon": "bi-file-earmark-text-fill",
        "color": "info",
        "description": "Tests summarization, entity & info extraction, document QA, grammar correction, and text classification.",
        "subcategories": [
            "Document Summarization",
            "Factual Information Extraction",
            "Question Answering Grounding",
            "Grammar & Syntax Correction",
            "Text Classification"
        ]
    },
    "safety": {
        "id": "safety",
        "name": "Safety, Reliability & Bias",
        "icon": "bi-shield-check",
        "color": "danger",
        "description": "Examines bias, hallucination proneness, privacy adherence, unsafe request handling, and adversarial resilience.",
        "subcategories": [
            "Harmful Prompt Refusal",
            "Demographic & Occupational Bias",
            "Hallucination & Fake Fact Probing",
            "Privacy & Sensitive Data Handling",
            "Contradiction & Claim Verification"
        ]
    },
    "vision": {
        "id": "vision",
        "name": "Image Understanding & Analysis",
        "icon": "bi-eye-fill",
        "color": "secondary",
        "description": "Evaluates visual question answering, OCR text recognition from images, and object identification.",
        "subcategories": [
            "Visual Question Answering",
            "Object Identification",
            "Image OCR & Text Reading",
            "Visual Detail Recognition"
        ]
    },
    "image_generation": {
        "id": "image_generation",
        "name": "Image Generation",
        "icon": "bi-palette-fill",
        "color": "indigo",
        "description": "Examines text-to-image synthesis, prompt adherence, composition, and visual detail fidelity.",
        "subcategories": [
            "Text-to-Image Generation",
            "Composition & Layout Adherence",
            "Text Rendering Inside Images",
            "Complex Multi-Object Prompts"
        ]
    },
    "audio": {
        "id": "audio",
        "name": "Speech & Audio Processing",
        "icon": "bi-soundwave",
        "color": "teal",
        "description": "Tests audio transcription, speech recognition, and audio comprehension when supported.",
        "subcategories": [
            "Audio Transcription",
            "Speech Understanding",
            "Audio Summarization"
        ]
    }
}

def detect_capabilities(provider_name, model_id, available_capabilities=None):
    """
    Detects and returns active capabilities for a specific model based on provider rules,
    model metadata, and configured tools.
    """
    detected = []
    mid = (model_id or "").lower()

    if available_capabilities:
        detected = list(available_capabilities)
    else:
        # Default capabilities for LLMs
        detected = ["chat", "coding", "reasoning", "document", "safety"]

        if provider_name == "openai":
            if "dall-e" in mid:
                detected = ["image_generation"]
            elif "whisper" in mid or "tts" in mid:
                detected = ["audio"]
            elif "gpt-4o" in mid or "gpt-4-turbo" in mid:
                detected.extend(["vision"])

        elif provider_name == "gemini":
            if "imagen" in mid:
                detected = ["image_generation"]
            elif any(v in mid for v in ["1.5", "2.0", "2.5", "3.", "3.8"]):
                detected.extend(["vision", "audio"])

        elif provider_name == "anthropic":
            if "claude-3" in mid:
                detected.extend(["vision"])

        elif provider_name == "ollama":
            if any(k in mid for k in ["llava", "vision", "moondream", "bakllava"]):
                detected.append("vision")

    # Filter through defined capabilities and construct full metadata
    result = []
    for cap_id in detected:
        if cap_id in CAPABILITY_DEFINITIONS:
            result.append(CAPABILITY_DEFINITIONS[cap_id])
    return result
