# Voice-to-Voice Offline LLM Interviewer

Professional lightweight offline interviewer pipeline built in Python:
- Parses JD and resume
- Extracts core skills + project signals
- Asks multiple interview questions aligned to skills/projects
- Collects answers via speech (Vosk) or keyboard fallback
- Generates follow-up / clarifying questions via local Llama model
- Saves transcript

## 🔧 Architecture & Behavior

1. Parse JD and resume text.
2. Extract skills and project snippets with heuristics.
3. Build initial question based on overlapping skill set.
4. Ask question:
   - TTS using `pyttsx3` (if available and voice mode enabled)
   - Listen using `vosk` + `sounddevice` (if available)
   - Or text input fallback
5. Use offline LLM (`llama-cpp-python`) to generate follow-up questions.
6. Continue for configured question limit.
7. Save transcript.

## 🧩 Requirements

- Python 3.9+
- `pip install -r requirements.txt`
- Offline Llama model file (e.g., `ggml-model-q4_0.bin`) in local path
- Vosk acoustic model folder for ASR (recommended): `model` or custom path

### Suggested model sources
- Llama family offline models (for non-commercial, license-allowed usage)
- Vosk models: https://alphacephei.com/vosk/models

## 📁 Key files

- `interviewer.py` - main CLI
- `web_ui.py` - Streamlit UI (resume PDF upload + JD field extraction)
- `requirements.txt` - dependencies
- `README.md` - this file

## ▶️ Usage

1. Install requirements:
```bash
pip install -r requirements.txt
```

2. Run UI:
```bash
streamlit run web_ui.py
```

UI includes:
- Resume PDF upload + text parsing
- Editable parsed resume text
- JD text input
- Extracted JD table: company, role, location
- Separate extracted job description section

3. Prepare inputs:
- Job description: plain text file or string
- Resume: plain text file or string

4. Run interviewer:
```bash
python interviewer.py \
  --job-description path/to/jd.txt \
  --resume path/to/resume.txt \
  --model path/to/ggml-model.bin \
  --vosk-model path/to/vosk-model \
  --output transcript.txt
```

5. Optional: text-only mode (no voice I/O):
```bash
python interviewer.py --no-voice --job-description ... --resume ... --model ...
```

## 📌 Command-line options

- `--job-description`, `-j`: JD text or filepath
- `--resume`, `-r`: resume text or filepath
- `--model`, `-m`: offline Llama model file path
- `--vosk-model`: Vosk model folder
- `--max-questions`: maximum Q/A cycles (default 10)
- `--output`, `-o`: transcript output path (default `transcript.txt`)
- `--no-voice`: disable TTS/STT and use terminal text input only

## 🧠 How it behaves like a 20-year recruiter

- Focuses on experience listed in resume and JD.
- Picks overlap between required and existing skills for first question.
- Generates follow-up questions from candidate responses.
- Insists on concrete details, tools, tradeoffs, metrics, and architecture.

## ⚙️ Model tuning

Prompts are hard-coded in `interviewer.py`:
- initial question from skill overlap
- follow-ups generated using Llama prompt that forces relevance to resume/JD

## 🛠️ Troubleshooting

- `ModuleNotFoundError`: check `pip install -r requirements.txt`.
- `LLM model not found`: ensure correct `--model` path.
- Vosk STT fail: put model in folder and run with `--vosk-model <path>`.
- Audio capture issues: verify microphone permissions and use text fallback with `--no-voice`.

## 💬 Example files

Create sample files:
- `sample_jd.txt`
- `sample_resume.txt`

Then run:
```bash
python interviewer.py -j sample_jd.txt -r sample_resume.txt -m ./ggml-model.bin
```

## 🧾 Transcript output

- Written to `transcript.txt` by default with Q1/A1... format.
- Use for recruiter review or QA.

---

Built for secure offline interviewing workflows with strict context-bound question generation.
