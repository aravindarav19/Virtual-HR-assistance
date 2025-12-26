import os
import csv
import streamlit as st
from datetime import datetime
from openai import OpenAI

# Optional PDF reader
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

# -----------------------------
# Page config (no sidebar)
# -----------------------------
st.set_page_config(
    page_title="AI-powered HR Assistant",
    layout="centered",
    initial_sidebar_state="collapsed"  # 👈 hides sidebar completely
)

# -----------------------------
# Load API key (BACKEND ONLY)
# -----------------------------
DEEPSEEK_API_KEY = (
    st.secrets.get("DEEPSEEK_API_KEY")
    or os.environ.get("DEEPSEEK_API_KEY")
)

if not DEEPSEEK_API_KEY:
    st.error(
        "System configuration error: API key not found.\n\n"
        "Please contact the administrator."
    )
    st.stop()

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

MODEL = "deepseek-chat"  # fixed internally

# -----------------------------
# HR Knowledge Base
# -----------------------------
HR_KNOWLEDGE = """
• Employees get 24 paid leave days per year.
• Remote work is allowed up to 2 days per week.
• Working hours are 9 AM–6 PM, Monday to Friday.
• UK public holidays are observed.
• Leave eligibility starts after 3 months.
• Health insurance is provided by Bupa.
• For support, contact hr@konantech.com or your manager.
""".strip()

# -----------------------------
# Mood helpers
# -----------------------------
def detect_mood(text: str):
    text = text.lower()
    if any(x in text for x in ["stressed", "overwhelmed", "burnt out"]):
        return "stress"
    if any(x in text for x in ["sad", "depressed", "down"]):
        return "sad"
    if any(x in text for x in ["tired", "exhausted"]):
        return "tired"
    return None

MOOD_RESPONSES = {
    "stress": "I’m sorry you’re feeling stressed. Consider taking a short break or speaking with your manager or HR.",
    "sad": "I’m sorry you’re feeling this way. You’re not alone — support is available.",
    "tired": "It sounds like you’ve been working hard. Rest and recovery are important.",
}

def is_checkin(text: str):
    return any(x in text.lower() for x in ["check in", "mood", "how am i doing"])

def log_mood(score: int):
    with open("mood_log.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().isoformat(), score])

# -----------------------------
# UI Header
# -----------------------------
st.title("AI-powered HR Assistant")
st.caption("Ask about HR policy, leave, remote work, or request a mood check-in.")

with st.expander("HR Policy Reference"):
    st.markdown(HR_KNOWLEDGE)

# -----------------------------
# Resume upload (optional)
# -----------------------------
resume_text = ""
resume = st.file_uploader("Upload your resume (optional)", type=["pdf", "txt"])

if resume:
    if resume.type == "application/pdf" and fitz:
        doc = fitz.open(stream=resume.read(), filetype="pdf")
        resume_text = "\n".join(p.get_text() for p in doc)
    elif resume.type == "text/plain":
        resume_text = resume.read().decode("utf-8", errors="ignore")

# -----------------------------
# Session state
# -----------------------------
if "history" not in st.session_state:
    st.session_state.history = []

if "pending_checkin" not in st.session_state:
    st.session_state.pending_checkin = False

# -----------------------------
# Display chat
# -----------------------------
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -----------------------------
# Chat input (ENTER submits)
# -----------------------------
user_text = st.chat_input("Type your message and press Enter…")
if not user_text:
    st.stop()

text = user_text.strip()
st.session_state.history.append({"role": "user", "content": text})

with st.chat_message("user"):
    st.markdown(text)

# -----------------------------
# Fast paths
# -----------------------------
if text.lower() in {"hi", "hello", "hey"}:
    reply = "Hello. Ask me about leave, HR policy, or upload your CV for feedback."
    st.session_state.history.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.markdown(reply)
    st.stop()

mood = detect_mood(text)
if mood:
    reply = MOOD_RESPONSES[mood]
    st.session_state.history.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.markdown(reply)
    st.stop()

if is_checkin(text):
    st.session_state.pending_checkin = True
    reply = "On a scale of 1–10, how are you feeling today?"
    st.session_state.history.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.markdown(reply)
    st.stop()

if st.session_state.pending_checkin:
    try:
        score = int(text)
        if 1 <= score <= 10:
            log_mood(score)
            st.session_state.pending_checkin = False
            reply = f"Thanks — I’ve logged your mood as {score}/10."
        else:
            raise ValueError
    except ValueError:
        reply = "Please enter a number between 1 and 10."

    st.session_state.history.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.markdown(reply)
    st.stop()

# -----------------------------
# LLM call
# -----------------------------
prompt = f"""
You are an HR assistant.
Use the HR policy and resume (if any) to answer clearly and professionally.

HR POLICY:
{HR_KNOWLEDGE}

RESUME:
{resume_text[:3000]}

USER QUESTION:
{text}
""".strip()

with st.chat_message("assistant"):
    with st.spinner("Thinking..."):
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.2,
        )
        reply = response.choices[0].message.content.strip()
        st.markdown(reply)
        st.session_state.history.append({"role": "assistant", "content": reply})
