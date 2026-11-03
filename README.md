# AI-Powered AI Model Testing, Evaluation and Investigation Agent

A full-stack web application designed for AI engineers and developers to select **one AI model at a time**, probe its capabilities, evaluate accuracy, detect failure modes, measure latency, assess bias, check safety adherence, and generate downloadable investigation reports (PDF/CSV).

---

## 🌟 Key Features

1. **Single-Model Forensic Evaluation**: Rigorously tests the single AI model selected by the user rather than generic leaderboard comparisons.
2. **Multi-Provider Support**:
   - Google Gemini (`gemini-3.8-flash`, `gemini-2.5-flash`, `gemini-2.5-pro`, etc.)
   - OpenAI (`gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `dall-e-3`)
   - Anthropic Claude (`claude-3-5-sonnet`, `claude-3-5-haiku`, `claude-3-opus`)
   - Ollama Local Models (`llama3`, `mistral`, `qwen2.5-coder`, `llava`)
   - Custom OpenAI-compatible API endpoints
3. **Comprehensive Capability Domains**:
   - **Chatbot & Conversation**: QA, multi-turn dialogue, context retention, instruction following, ambiguity.
   - **Coding & Programming**: Generation, bug identification, and **isolated Python subprocess sandbox execution**.
   - **Reasoning & Problem-Solving**: Multi-step deduction, math word problems, fallacies & contradictions.
   - **Document & Text Processing**: Summarization, factual extraction, grounding vs hallucination.
   - **Safety, Reliability & Bias**: Occupational/demographic bias checks, fake entity hallucination probing, harmful prompt refusals.
   - **Image Generation & Vision**: Multi-modal testing when supported by the active model.
4. **Forensic Failure Investigation**:
   - Categorizes outputs into *Correct, Partially correct, Incorrect, Unsupported, Failed execution, Requires human review*.
   - Explains detected issues, provides supporting evidence, assigns severity levels (Low, Medium, High, Critical), confidence percentage, and actionable recommendations.
5. **Interactive Dashboard & Charts**:
   - Built with Chart.js: Capability radar fingerprints and latency/failure bar charts.
   - Reliability levels: **HIGH (80–100)**, **MEDIUM (50–79)**, **LOW (<50)**.
6. **Downloadable Reports & History**:
   - Download official evaluation reports as **PDF** (via ReportLab) and **CSV**.
   - Persistent test history stored in SQLite.

---

## 🚀 Step-by-Step Instructions for Visual Studio Code on Windows

### 1. Open Project in Visual Studio Code
Open Visual Studio Code, click **File > Open Folder...**, and select:
```
C:\Users\vigne\.gemini\antigravity\scratch\ai-testing-agent
```

### 2. Open Integrated Terminal
Press `` Ctrl + ` `` (or select **Terminal > New Terminal**).

### 3. Install Dependencies
All required dependencies (`Flask`, `Flask-CORS`, `requests`, `python-dotenv`, `reportlab`, `pillow`) are already installed. If needed, you can reinstall via:
```bash
python -m pip install -r backend/requirements.txt
```

### 4. Run the Application
Start the Flask application server by running:
```bash
python run.py
```

### 5. Access the Web Dashboard
Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🧭 Application Walkthrough

1. **Dashboard (`/dashboard`)**: Overview of the active model, latest reliability score, latency, and capability distributions.
2. **Select AI Model (`/select-model`)**: Connect to your preferred provider (Gemini, OpenAI, Claude, Ollama, or Custom API), test the connection with a live ping, and activate the model.
3. **Model Capabilities (`/capabilities`)**: View active vs unsupported capabilities dynamically detected for the chosen model.
4. **Test Configuration (`/test-config`)**: Select capabilities to probe, adjust test case counts, choose difficulties (Normal, Hard, Edge Cases), and customize prompts.
5. **Run Tests (`/run-tests`)**: Live execution engine with animated progress bar, real-time response streaming, and sandbox verification.
6. **Investigation Results (`/investigation`)**: Deep-dive into failure logs, hallucination detections, evidence, severity levels, and prompt-tuning recommendations.
7. **Performance Analysis (`/analysis`)**: Multi-domain radar chart and latency distribution across capabilities.
8. **Reports (`/reports`)**: Download ready-to-share PDF and CSV evaluation reports.
9. **Test History (`/history`)**: Revisit any past test session from SQLite.
10. **Settings (`/settings`)**: Securely manage API keys, Ollama server URL, and reliability score thresholds.
