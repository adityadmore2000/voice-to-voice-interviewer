#!/usr/bin/env python3
import re
from io import BytesIO

import pandas as pd
import streamlit as st
from pypdf import PdfReader


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_pdf_text(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    chunks = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    return clean_text("\n".join(chunks))


def extract_field(lines, field_aliases):
    field_regex = "|".join(re.escape(alias) for alias in field_aliases)
    pattern = re.compile(rf"(?i)^\s*(?:{field_regex})\s*[:\-]\s*(.+?)\s*$")
    for line in lines:
        match = pattern.match(line.strip())
        if match:
            return match.group(1).strip()
    return ""


def extract_role_from_text(text: str) -> str:
    role_patterns = [
        r"(?i)\b(job\s*title|title|position|role)\s*[:\-]\s*([^\n]+)",
        r"(?i)\b(hiring|looking)\s+(for|an?|the)\s+([A-Za-z0-9 /,&\-\(\)]+)",
        r"(?i)\b(seeking)\s+an?\s+([A-Za-z0-9 /,&\-\(\)]+)",
    ]
    for pat in role_patterns:
        match = re.search(pat, text)
        if not match:
            continue
        if len(match.groups()) >= 3:
            candidate = match.group(3).strip()
        elif len(match.groups()) >= 2:
            candidate = match.group(2).strip()
        else:
            candidate = match.group(1).strip()
        if 2 <= len(candidate) <= 120:
            return candidate
    return ""


def extract_role_from_headline(lines) -> str:
    blocked_exact = {
        "about the job",
        "job description",
        "responsibilities",
        "required skills",
        "preferred",
        "preferred skills",
    }
    blocked_starts = (
        "experience",
        "location",
        "notice period",
        "responsibilities",
        "required skills",
        "preferred",
    )
    for line in lines[:10]:
        raw = line.strip().strip("-").strip()
        lowered = raw.lower()
        if not raw:
            continue
        if lowered in blocked_exact:
            continue
        if any(lowered.startswith(prefix) for prefix in blocked_starts):
            continue
        if re.search(r"(?i)\b(responsibilities|required skills|preferred skills)\b", raw):
            continue
        if 2 <= len(raw) <= 120 and len(raw.split()) <= 10:
            return raw
    return ""


def extract_jd_fields(jd_text: str):
    lines = [line.strip() for line in jd_text.splitlines() if line.strip()]
    company = extract_field(lines, ["company", "organization", "employer"])
    role = extract_field(lines, ["role", "job title", "position", "title"])
    location = extract_field(lines, ["location", "job location", "work location"])

    if not role:
        role = extract_role_from_text(jd_text)
    if not role:
        role = extract_role_from_headline(lines)

    metadata_prefixes = (
        "company:",
        "organization:",
        "employer:",
        "role:",
        "job title:",
        "position:",
        "title:",
        "location:",
        "job location:",
        "work location:",
    )
    description_lines = [line for line in lines if not line.lower().startswith(metadata_prefixes)]
    description = clean_text("\n".join(description_lines)) or clean_text(jd_text)

    return {
        "Company": company or "Not found",
        "Role": role or "Not found",
        "Location": location or "Not found",
        "Job Description": description or "Not found",
    }


def init_state_defaults():
    defaults = {
        "resume_text": "",
        "jd_text": "",
        "jd_company": "",
        "jd_role": "",
        "jd_location": "",
        "jd_description": "",
        "jd_source_text": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def main():
    st.set_page_config(page_title="Interview Input UI", page_icon="🧾", layout="wide")
    st.title("Resume + JD Intake")
    st.caption("Upload resume PDF, edit parsed resume text, and extract structured JD fields.")

    init_state_defaults()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Resume PDF")
        uploaded_pdf = st.file_uploader("Upload Resume (PDF)", type=["pdf"])
        if uploaded_pdf is not None:
            try:
                parsed_resume = parse_pdf_text(uploaded_pdf.read())
                st.session_state.resume_text = parsed_resume
                st.success("PDF parsed successfully.")
            except Exception as exc:
                st.error(f"Could not parse PDF: {exc}")

        st.session_state.resume_text = st.text_area(
            "Resume Text (Editable)",
            value=st.session_state.resume_text,
            height=380,
            placeholder="Parsed resume text appears here after PDF upload...",
        )

    with col2:
        st.subheader("Job Description (Text)")
        jd_text = st.text_area(
            "Paste JD Text",
            height=380,
            placeholder="Paste complete job description text here...",
            key="jd_text",
        )

        should_extract = False
        if jd_text.strip() and not st.session_state.jd_source_text:
            should_extract = True
        if st.button("Extract / Refresh Fields from JD"):
            should_extract = bool(jd_text.strip())

        if should_extract:
            extracted = extract_jd_fields(jd_text)
            st.session_state.jd_company = extracted["Company"] if extracted["Company"] != "Not found" else ""
            st.session_state.jd_role = extracted["Role"] if extracted["Role"] != "Not found" else ""
            st.session_state.jd_location = extracted["Location"] if extracted["Location"] != "Not found" else ""
            st.session_state.jd_description = (
                extracted["Job Description"] if extracted["Job Description"] != "Not found" else ""
            )
            st.session_state.jd_source_text = jd_text

        st.markdown("### Extracted JD Details (Editable)")
        st.text_input("Company", key="jd_company")
        st.text_input("Role", key="jd_role")
        st.text_input("Location", key="jd_location")
        st.text_area("Job Description", key="jd_description", height=200)

        st.markdown("### Extracted JD Details")
        st.table(
            pd.DataFrame(
                [
                    {
                        "Company": st.session_state.jd_company or "Not found",
                        "Role": st.session_state.jd_role or "Not found",
                        "Location": st.session_state.jd_location or "Not found",
                    }
                ]
            )
        )

    st.divider()
    st.markdown("### Final Parsed Inputs")
    st.text_area("Final Resume Text", value=st.session_state.resume_text, height=220)
    st.text_area("Final JD Description", value=st.session_state.jd_description, height=220)


if __name__ == "__main__":
    main()
