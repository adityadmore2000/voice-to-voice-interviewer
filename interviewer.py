#!/usr/bin/env python3
import argparse
import json
import os
import re
from pathlib import Path

from rich.console import Console

console = Console()

# Optional voice libs
try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    import sounddevice as sd
except ImportError:
    sd = None

try:
    from vosk import KaldiRecognizer, Model
except ImportError:
    KaldiRecognizer = None
    Model = None

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None


def load_text(input_str: str):
    if os.path.exists(input_str):
        return Path(input_str).read_text(encoding="utf-8")
    return input_str


def sanitize_text(text):
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def extract_skills_projects(text: str):
    text_lower = text.lower()
    skills = set()
    projects = []

    lines = text.splitlines()
    for i, line in enumerate(lines):
        if any(keyword in line.lower() for keyword in ("skill", "technolog", "tool", "experience")):
            line_clean = re.sub(r"[^a-zA-Z0-9+/#,.- ]", "", line)
            candidates = re.split(r"[,;|/-]", line_clean)
            for candidate in candidates:
                token = candidate.strip()
                if token and 1 < len(token) < 80 and len(token.split()) <= 5:
                    skills.add(token)

        if "project" in line.lower() or "experience" in line.lower() or "work" in line.lower():
            window = " ".join(lines[i : min(i + 5, len(lines))])
            if 30 < len(window) < 500:
                projects.append(window.strip())

    if not skills:
        common_skills = [
            "Python",
            "Java",
            "C++",
            "C#",
            "JavaScript",
            "TypeScript",
            "Go",
            "Rust",
            "Docker",
            "Kubernetes",
            "AWS",
            "GCP",
            "Azure",
            "React",
            "Node",
            "Django",
            "Flask",
            "SQL",
            "PostgreSQL",
            "MongoDB",
            "Git",
            "Linux",
            "Pytest",
        ]
        for skill in common_skills:
            if skill.lower() in text_lower:
                skills.add(skill)

    if not projects:
        paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
        projects = paragraphs[:2]

    return sorted(skills), projects


def init_tts():
    if pyttsx3 is None:
        return None
    engine = pyttsx3.init()
    engine.setProperty("rate", 150)
    engine.setProperty("volume", 1.0)
    return engine


def speak(engine, text):
    if engine is None:
        return
    engine.say(text)
    engine.runAndWait()


def stt_listen(duration=10, model_path=""):
    if Model is None or KaldiRecognizer is None or sd is None:
        return None
    if model_path and not os.path.exists(model_path):
        raise FileNotFoundError(f"Vosk model not found at {model_path}")
    model = Model(model_path or "model")
    rec = KaldiRecognizer(model, 16000)
    console.print("[green]Listening for your spoken answer...[/green]")
    recording = sd.rec(int(duration * 16000), samplerate=16000, channels=1)
    sd.wait()
    data = recording.tobytes()
    if rec.AcceptWaveform(data):
        result = json.loads(rec.Result())
        return result.get("text", "")
    result = json.loads(rec.FinalResult())
    return result.get("text", "")


def create_llm(model_path):
    if Llama is None:
        raise RuntimeError("llama-cpp-python is required; run pip install -r requirements.txt")
    if not model_path or not os.path.exists(model_path):
        raise FileNotFoundError(f"LLM model not found at {model_path}")
    return Llama(model_path=model_path, n_ctx=4096)


def llm_generate(llm, prompt, max_tokens=220, temperature=0.8):
    resp = llm(prompt=prompt, max_tokens=max_tokens, temperature=temperature)
    output = resp["choices"][0]["text"].strip()
    return output


def pick_focus_skill(jd_skills, resume_skills):
    for s in resume_skills:
        if s in jd_skills:
            return s
    if resume_skills:
        return resume_skills[0]
    if jd_skills:
        return jd_skills[0]
    return None


def make_initial_question(jd_skills, resume_skills, projects):
    focus = pick_focus_skill(jd_skills, resume_skills)
    if focus:
        return (
            f"Tell me about a project where you directly used '{focus}' and the measurable impact you achieved."
        )
    if projects:
        return "Tell me about the most recent project in your background and the technical stack used."
    return "Describe your strongest technical project and how it relates to the job requirements."


def make_followup_question(answer, jd_skills, resume_skills, projects):
    skill_list = ", ".join(jd_skills if jd_skills else resume_skills)
    prompt = (
        "You are an expert technical recruiter. Based on candidate answer below, generate exactly one follow-up question. "
        "Questions must be focused strictly on skills or projects from the candidate resume or job description, and seek clarification or deeper technical understanding.\n\n"
        f"Job/Resume skills: {skill_list}\n"
        f"Candidate answer: {answer}\n"
        "If the answer is generic, ask for concrete tools, metrics, architecture, trade-offs, or lessons learned. "
        "If the answer already has sufficient structure, ask one advanced follow-up that tests depth. "
    )
    return prompt


def save_transcript(transcript_lines, outpath):
    if not outpath:
        return
    Path(outpath).write_text("\n".join(transcript_lines), encoding="utf-8")


def ask_question(question, engine=None, vosk_model_path=""):
    console.print(f"[bold blue]Interviewer:[/bold blue] {question}")
    speak(engine, question)
    answer = None

    if not engine and (Model is None or KaldiRecognizer is None or sd is None):
        answer = console.input("[bold green]Your answer (type):[/bold green] ")
        return answer.strip()

    if Model is not None and KaldiRecognizer is not None and sd is not None:
        try:
            speech = stt_listen(duration=12, model_path=vosk_model_path)
            if speech and speech.strip():
                return speech.strip()
        except Exception as e:
            console.print(f"[yellow]STT error {e}; switching to typed input.[/yellow]")

    answer = console.input("[bold green]Your answer (type):[/bold green] ")
    return answer.strip()


def main():
    parser = argparse.ArgumentParser(description="Offline voice-to-voice LLM interviewer")
    parser.add_argument("--job-description", "-j", required=True, help="Job description text or file path")
    parser.add_argument("--resume", "-r", required=True, help="Candidate resume text or file path")
    parser.add_argument("--model", "-m", required=True, help="Path to offline Llama model file (ggml).")
    parser.add_argument("--vosk-model", help="Path to Vosk model folder for ASR", default="")
    parser.add_argument("--max-questions", type=int, default=10, help="Max total questions")
    parser.add_argument("--output", "-o", default="transcript.txt", help="Transcript output file")
    parser.add_argument("--no-voice", action="store_true", help="No speech TTS/STT available")
    args = parser.parse_args()

    jd_text = sanitize_text(load_text(args.job_description))
    resume_text = sanitize_text(load_text(args.resume))

    jd_skills, _ = extract_skills_projects(jd_text)
    resume_skills, resume_projects = extract_skills_projects(resume_text)

    llm = create_llm(args.model)
    tts_engine = None if args.no_voice else init_tts()

    console.print("[bold underline]Voice-to-Voice Offline Interviewer[/bold underline]\n")
    console.print("[cyan]JD skills:[/cyan]", ", ".join(jd_skills) or "(none)")
    console.print("[cyan]Resume skills:[/cyan]", ", ".join(resume_skills) or "(none)")
    console.print("[cyan]Resume projects sample:[/cyan]\n", "\n".join(resume_projects[:3]) or "(none)")

    transcript = []
    previous_answer = ""

    question = make_initial_question(jd_skills, resume_skills, resume_projects)
    for qnum in range(1, args.max_questions + 1):
        transcript.append(f"Q{qnum}: {question}")
        answer = ask_question(question, None if args.no_voice else tts_engine, vosk_model_path=args.vosk_model)
        transcript.append(f"A{qnum}: {answer}")

        if answer.strip().lower() in {"exit", "quit", "stop", "done"}:
            console.print("[bold yellow]Candidate ended the interview.[/bold yellow]")
            break

        previous_answer = answer

        followup_prompt = make_followup_question(previous_answer, jd_skills, resume_skills, resume_projects)
        question = llm_generate(llm, followup_prompt)

    save_transcript(transcript, args.output)
    console.print(f"[bold green]Done. Transcript saved to {args.output}[/bold green]")


if __name__ == "__main__":
    main()
