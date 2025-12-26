import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from openai import OpenAI
from datetime import datetime
import csv
import os
import traceback

# Optional dependencies (PDF + TTS). App will still run without them.
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from gtts import gTTS
    from tempfile import NamedTemporaryFile
except Exception:
    gTTS = None
    NamedTemporaryFile = None

# -----------------------------
# 🔐 API Setup (DeepSeek via OpenAI-compatible SDK)
# -----------------------------
st.set_page_config(page_title="AI-powered HR Assistant", layout="centered")

if "DEEPSEEK_API_KEY" not in st.secrets:
    st.error("Missing DEEPSEEK_API_KEY in Streamlit Secrets.")
    st.stop()

DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

MODEL = "deepseek-chat"        # general-purpose
# MODEL = "deepseek-reasoner"  # heavier reasoning (if enabled on your account)

# -----------------------------
# 📘 HR Knowledge Base
# -----------------------------
HR_KNOWLEDGE = """
🏢  HR Policy Summary:

• Employees get 24 paid leave days per year.
• Remote work is allowed up to 2 days per week.
• Working hours are 9 AM to 6 PM (Monday to Friday).
• Official holidays follow the UK calendar.
• New employees are eligible for leave after 3 months.
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
        "stress": ["i'm stressed", "im stressed", "feeling stressed", "so much pressure", "overwhelmed", "burnt out"],
        "anxiety": ["anxious", "worried", "panic", "nervous"],
        "sad": ["sad", "feeling down", "depressed", "hopeless"],
        "tired": ["tired", "exhausted", "drained", "no energy"],
    }
    for mood, phrases in mood_map.items():
        if any(p in text for p in phrases):
            return mood
    return None

mood_responses = {
    "stress": "I’m sorry you’re feeling stressed. Consider taking a short break, breathing slowly, and prioritising one task at a time. If it would help, speak with your manager or HR.",
    "anxiety": "Anxiety can be difficult. Take it step by step and be kind to yourself. If it persists or escalates, consider speaking with your manager or HR.",
    "sad": "I’m sorry you’re feeling this way. It’s okay to not be okay sometimes. If you’d like, consider speaking with your manager or HR for support.",
    "tired": "It sounds like you’ve been working hard. If possible, take a break, hydrate, and make sure you’re getting enough rest.",
}

def is_checkin_request(text: str) -> bool:
    checkin_keywords = [
        "check in", "check-in", "how am i doing", "how i'm doing", "not feeling good",
        "motivate me", "motivation", "i’m unproductive", "im unproductive", "i feel off",
        "mood check", "mood check-in", "check my mood"
    ]
    text = (text or "").lower()
    return any(phrase in text for phrase in checkin_keywords)

def log_mood_to_csv(mood_score: int, filepath: str = "mood_log.csv"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_exists = os.path.exists(filepath)
    with open(filepath, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Mood"])
        writer.writerow([timestamp, mood_score])

# -----------------------------
# 🔊 Optional TTS
# -----------------------------
def speak_text(text: str):
    """Return a filepath to an MP3 of the text, or None if TTS not available."""
    if gTTS is None or NamedTemporaryFile is None:
        return None
    try:
        tts = gTTS(text=text, lang="en")
        tmp = NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp.name)
        return tmp.name
    except Exception:
        return None

# -----------------------------
# 🌟 Session State
# -----------------------------
if "history" not in st.session_state:
    st.session_state.history = []  # list of dicts: {"role": "user"/"assistant", "content": "..."}
if "pending_checkin" not in st.session_state:
    st.session_state.pending_checkin = False

# -----------------------------
# 🌟 UI
# -----------------------------
st.title("AI-powered HR Assistant")
st.write("Ask about HR policy, leave, remote work, CV feedback, or run a quick mood check-in.")

with st.expander("HR Policy (Reference)", expanded=False):
    st.markdown(HR_KNOWLEDGE)

# -----------------------------
# 📄 Resume upload (optional)
# -----------------------------
st.markdown("### Upload Your Resume (Optional)")
resume_file = st.file_uploader("Upload your resume (PDF or .txt)", type=["pdf", "txt"])
resume_text = ""

if resume_file:
    try:
        if resume_file.type == "application/pdf":
            if fitz is None:
                st.warning("PDF reading requires PyMuPDF. Add 'PyMuPDF' to requirements.txt.")
            else:
                doc = fitz.open(stream=resume_file.read(), filetype="pdf")
                for page in doc:
                    resume_text += page.get_text()
                st.success("Resume uploaded successfully!")
        elif resume_file.type == "text/plain":
            resume_text = resume_file.read().decode("utf-8", errors="ignore")
            st.success("Resume uploaded successfully!")
    except Exception as e:
        st.warning(f"Could not read resume: {e}")

st.divider()

# -----------------------------
# 💬 Chat History Display
# -----------------------------
st.markdown("### Conversation")
for msg in st.session_state.history:
    if msg["role"] == "user":
        st.markdown(f"**You:** {msg['content']}")
    else:
        st.markdown(f"**Assistant:** {msg['content']}")

st.divider()

# -----------------------------
# 💬 User input + submit
# -----------------------------
user_input = st.text_input("Type your message")
send = st.button("Send")

if not send:
    st.stop()

text = (user_input or "").strip()
if not text:
    st.warning("Please type a message.")
    st.stop()

# Save user message
st.session_state.history.append({"role": "user", "content": text})

# -----------------------------
# ✅ Handle greetings
# -----------------------------
if text.lower() in {"hi", "hello", "hey"}:
    reply = "Hello. Ask me something like: ‘How many leave days do I get?’ or ‘Can you review my CV summary?’"
    st.session_state.history.append({"role": "assistant", "content": reply})
    st.rerun()

# -----------------------------
# ✅ Mood detection quick response
# -----------------------------
mood = detect_mood(text)
if mood:
    reply = mood_responses[mood]
    st.session_state.history.append({"role": "assistant", "content": reply})
    st.rerun()

# -----------------------------
# ✅ Check-in flow
# -----------------------------
if is_checkin_request(text):
    st.session_state.pending_checkin = True
    reply = "On a scale of 1–10, how are you feeling today? Type a number and press Send."
    st.session_state.history.append({"role": "assistant", "content": reply})
    st.rerun()

if st.session_state.pending_checkin:
    try:
        score = int(text)
        if not (1 <= score <= 10):
            raise ValueError

        log_mood_to_csv(score)
        st.session_state.pending_checkin = False
        reply = (
            f"Thanks — I’ve logged your mood as **{score}/10**.\n\n"
            "If you’d like, tell me what’s driving that score today and I’ll suggest practical next steps."
        )
        st.session_state.history.append({"role": "assistant", "content": reply})
        st.rerun()
    except Exception:
        reply = "Please enter a whole number from **1 to 10**."
        st.session_state.history.append({"role": "assistant", "content": reply})
        st.rerun()

# -----------------------------
# 🤖 DeepSeek answer (policy + resume + chat context)
# -----------------------------
# Keep context short to avoid token bloat
recent_history = st.session_state.history[-10:]
history_text = "\n".join(
    [f"{m['role'].upper()}: {m['content']}" for m in recent_history]
)

prompt = f"""
You are an HR assistant for a UK-based company.
Use the HR policy and the resume text (if any) to answer accurately.
If the user asks for policy, cite the relevant bullet(s).
If the question is unclear, ask ONE clarifying question.
Keep the tone professional and supportive.

HR POLICY:
{HR_KNOWLEDGE}

RESUME (optional, may be empty):
{resume_text[:4000]}

CONVERSATION CONTEXT:
{history_text}

Now answer the latest USER message: "{text}"
""".strip()

with st.spinner("Thinking..."):
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=700,
            temperature=0.2,
        )
        reply = (resp.choices[0].message.content or "").strip()

        if not reply:
            reply = "I didn’t receive a usable response from the model. Please try again."

        st.session_state.history.append({"role": "assistant", "content": reply})
        st.rerun()

    except Exception as e:
        st.error("DeepSeek request failed.")
        st.exception(e)
        # Also add a friendly message into history so the user sees something
        st.session_state.history.append(
            {"role": "assistant", "content": "Sorry — the request failed. Please try again in a moment."}
        )
        st.stop()

# -----------------------------
# (Optional) TTS playback section (not reached due to st.rerun above)
# If you want TTS, move this to display after rendering history.
# -----------------------------
