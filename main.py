import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from openai import OpenAI
from datetime import datetime
from gtts import gTTS
from tempfile import NamedTemporaryFile
import fitz  # PyMuPDF
import csv
import os
import traceback

# -----------------------------
# 🔐 API Setup (DeepSeek)
# -----------------------------
st.set_page_config(page_title="AI-powered HR Assistant", layout="centered")

# In .streamlit/secrets.toml add:
# DEEPSEEK_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxx"
DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

# Choose one:
MODEL = "deepseek-chat"        # general-purpose
# MODEL = "deepseek-reasoner"  # heavier reasoning

# -----------------------------
# 📘 HR Knowledge Base
# -----------------------------
HR_KNOWLEDGE = """
🏢  HR Policy Summary:

• Employees get **24 paid leave days** per year.
• Remote work is allowed **up to 2 days per week**.
• Working hours are **9 AM to 6 PM (Monday to Friday)**.
• Official holidays follow the UK calendar.
• New employees are eligible for leave **after 3 months**.
• Health insurance is provided by Bupa.
• For emotional support, contact hr@konantech.com or your manager.
• Job descriptions are available in the internal portal (portal.konantech.com).
• Employees are expected to follow the code of conduct and report violations.
""".strip()

# -----------------------------
# 🧠 Mood detection logic
# -----------------------------
def detect_mood(text: str):
    text = (text or "").lower()
    mood_map = {
        "stress": ["i'm stressed", "feeling stressed", "so much pressure", "overwhelmed", "burnt out"],
        "anxiety": ["anxious", "worried", "panic", "nervous"],
        "sad": ["sad", "feeling down", "depressed", "hopeless"],
        "tired": ["tired", "exhausted", "drained", "no energy"],
    }
    for mood, phrases in mood_map.items():
        if any(p in text for p in phrases):
            return mood
    return None

mood_responses = {
    "stress": "I'm sorry you're feeling stressed. You're not alone. Consider taking a short break, breathing slowly, or speaking with your manager or HR if it would help.",
    "anxiety": "Anxiety can be difficult. Take it one step at a time and be kind to yourself. If it persists, consider speaking with your manager or HR.",
    "sad": "I'm sorry you're feeling this way. It's okay to not be okay sometimes. If you’d like, you can speak with your manager or HR for support.",
    "tired": "It sounds like you've been working hard. If possible, take a break, hydrate, and make sure you’re getting enough rest.",
}

def is_checkin_request(text: str) -> bool:
    checkin_keywords = [
        "check in", "check-in", "how am i doing", "not feeling good",
        "motivate me", "motivation", "i’m unproductive", "i feel off"
    ]
    text = (text or "").lower()
    return any(phrase in text for phrase in checkin_keywords)

def log_mood_to_csv(mood_score: int):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_exists = os.path.exists("mood_log.csv")
    with open("mood_log.csv", mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        # Optional header (only if file newly created)
        if not file_exists:
            writer.writerow(["Timestamp", "Mood"])
        writer.writerow([timestamp, mood_score])

# -----------------------------
# 🌟 UI Start
# -----------------------------
if "history" not in st.session_state:
    st.session_state.history = []

if "pending_checkin" not in st.session_state:
    st.session_state.pending_checkin = False

st.title("👩‍💼 AI-powered HR Assistant")
st.write("Ask me anything about your job, leave policy, CV, or mood check-in.")

# -----------------------------
# 📄 Resume upload
# -----------------------------
st.markdown("### 📎 Upload Your Resume (Optional)")
resume_file = st.file_uploader("Upload your resume (PDF or .txt)", type=["pdf", "txt"])
resume_text = ""

if resume_file:
    try:
        if resume_file.type == "application/pdf":
            doc = fitz.open(stream=resume_file.read(), filetype="pdf")
            for page in doc:
                resume_text += page.get_text()
        elif resume_file.type == "text/plain":
            resume_text = resume_file.read().decode("utf-8", errors="ignore")
        st.success("Resume uploaded successfully!")
    except Exception as e:
        st.warning(f"Could not read resume: {e}")

# -----------------------------
# 💬 User input
# -----------------------------
user_input = st.text_input("👤 You:")

# If user already asked for a check-in, show the mood input
if st.session_state.pending_checkin:
    st.info("On a scale of 1–10, how are you feel)

