import os
import csv
import streamlit as st
from datetime import datetime
from openai import OpenAI

# Optional PDF reader (PyMuPDF). App still runs without it.
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(page_title="AI-powered HR Assistant", layout="centered")

# -----------------------------
# HR Knowledge Base
# -----------------------------
HR_KNOWLEDGE = """
🏢 HR Policy Summary (Internal):

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
# Mood utilities
# -----------------------------
def detect_mood(text: str):
    text = (text or "").lower()
    mood_map = {
        "stress": ["i'm stressed", "im stressed", "feeling stressed", "pressure", "overwhelmed", "burnt out", "burned out"],
        "anxiety": ["anxious", "worried", "panic", "nervous"],
        "sad": ["sad", "feeling down", "depressed", "hopeless"],
        "tired": ["tired", "exhausted", "drained", "no energy"],
    }
    for mood, phrases in mood_map.items():
        if any(p in text for p in phrases):
            return mood
    return None

MOOD_RESPONSES = {
    "stress": "I’m sorry you’re feeling stressed. Consider a short break, slow breathing, and prioritising one thing at a time. If helpful, speak with your manager or HR.",
    "anxiety": "Anxiety can be difficult. Take it step by step. If it persists or escalates, please consider speaking with your manager or HR.",
    "sad": "I’m sorry you’re feeling this way. If you’d like, consider speaking with your manager or HR for support.",
    "tired": "It sounds like you’ve been working hard. If possible, take a break, hydrate, and protect your rest.",
}

def is_checkin_request(text: str) -> bool:
    text = (text or "").lower()
    keywords = [
        "check in", "check-in", "mood check", "mood check-in",
        "how am i doing", "not feeling good", "motivate me", "motivation",
        "i feel off", "im unproductive", "i’m unproductive"
    ]
    return any(k in text for k in keywords)

def log_mood_to_csv(score: int, filepath: str = "mood_log.csv"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    exists = os.path.exists(filepath)
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["Timestamp", "Mood"])
        w.writerow([ts, score])

# -----------------------------
# API Key Loader (Secrets > Env > Manual)
# -----------------------------
def get_deepseek_key():
    # 1) Streamlit secrets
    if "DEEPSEEK_API_KEY" in st.secrets and str(st.secrets["DEEPSEEK_API_KEY"]).strip():
        return str(st.secrets["DEEPSEEK_API_KEY"]).strip()

    # 2) Environment variable
    env_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if env_key:
        return env_key

    return ""

# -----------------------------
# UI Header
# -----------------------------
st.title("AI-powered HR Assistant")
st.write("Ask about HR policy, leave, remote work, CV feedback, or run a quick mood check-in.")

with st.expander("HR Policy (Reference)"):
    st.markdown(HR_KNOWLEDGE)

# -----------------------------
# Sidebar: API setup + test
# -----------------------------
st.sidebar.header("Configuration")

auto_key = get_deepseek_key()
manual_key = st.sidebar.text_input(
    "DeepSeek API Key (only if not set in Secrets/Env)",
    value="",
    type="password",
    help="Prefer Streamlit Secrets: DEEPSEEK_API_KEY"
)

DEEPSEEK_API_KEY = manual_key.strip() if manual_key.strip() else auto_key

base_url = st.sidebar.selectbox(
    "Base URL",
    options=["https://api.deepseek.com", "https://api.deepseek.com/v1"],
    index=0,
    help="DeepSeek supports OpenAI-compatible base_url."
)

model = st.sidebar.selectbox(
    "Model",
    options=["deepseek-chat", "deepseek-reasoner"],
    index=0
)

if not DEEPSEEK_API_KEY:
    st.sidebar.warning("No API key detected yet (Secrets/Env/manual). The assistant cannot call DeepSeek.")

client = None
if DEEPSEEK_API_KEY:
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=base_url)

if st.sidebar.button("Test Connection"):
    if not client:
        st.sidebar.error("Add your API key first.")
    else:
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Reply with exactly: OK"}],
                max_tokens=10,
                temperature=0.0,
            )
            st.sidebar.success((r.choices[0].message.content or "").strip() or "(empty)")
        except Exception as e:
            st.sidebar.error("Connection test failed.")
            st.sidebar.exception(e)

# -----------------------------
# Resume upload (optional)
# -----------------------------
st.markdown("### Upload Your Resume (Optional)")
resume_file = st.file_uploader("Upload your resume (PDF or .txt)", type=["pdf", "txt"])
resume_text = ""

if resume_file is not None:
    try:
        if resume_file.type == "application/pdf":
            if fitz is None:
                st.warning("PDF support requires PyMuPDF. Add 'PyMuPDF' to requirements.txt or upload .txt instead.")
            else:
                doc = fitz.open(stream=resume_file.read(), filetype="pdf")
                resume_text = "\n".join([p.get_text() for p in doc])
                st.success("Resume uploaded successfully.")
        else:
            resume_text = resume_file.read().decode("utf-8", errors="ignore")
            st.success("Resume uploaded successfully.")
    except Exception as e:
        st.warning("Could not read resume.")
        st.exception(e)

st.divider()

# -----------------------------
# Session state for chat
# -----------------------------
if "history" not in st.session_state:
    st.session_state.history = []  # [{"role": "user"/"assistant", "content": "..."}]
if "pending_checkin" not in st.session_state:
    st.session_state.pending_checkin = False

# Display chat history
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

# Quick paths
if text.lower() in {"hi", "hello", "hey"}:
    reply = "Hello. Ask me something like: ‘How many leave days do I get?’ or ‘Can you review my CV summary?’"
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

if is_checkin_request(text):
    st.session_state.pending_checkin = True
    reply = "On a scale of 1–10, how are you feeling today? Type a number and press Enter."
    st.session_state.history.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.markdown(reply)
    st.stop()

if st.session_state.pending_checkin:
    try:
        score = int(text)
        if not (1 <= score <= 10):
            raise ValueError
        log_mood_to_csv(score)
        st.session_state.pending_checkin = False
        reply = f"Thanks — I’ve logged your mood as **{score}/10**. If you’d like, tell me what’s driving that score and I’ll suggest next steps."
        st.session_state.history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)
        st.stop()
    except Exception:
        reply = "Please enter a whole number from **1 to 10**."
        st.session_state.history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)
        st.stop()

# -----------------------------
# DeepSeek call
# -----------------------------
if not client:
    reply = "I can’t call DeepSeek yet because the API key is missing. Add it in Streamlit Secrets as **DEEPSEEK_API_KEY** (recommended), or paste it in the sidebar."
    st.session_state.history.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.markdown(reply)
    st.stop()

# Keep context small
recent = st.session_state.history[-12:]
context = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in recent])

prompt = f"""
You are an HR assistant for a UK-based company.
Use the HR policy and (if provided) the resume text to answer accurately and practically.
If the question is unclear, ask ONE clarifying question.

HR POLICY:
{HR_KNOWLEDGE}

RESUME (optional):
{resume_text[:4000]}

CONTEXT:
{context}
""".strip()

with st.chat_message("assistant"):
    with st.spinner("Thinking..."):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=700,
                temperature=0.2,
            )
            reply = (resp.choices[0].message.content or "").strip() or "Empty response returned."
            st.markdown(reply)
            st.session_state.history.append({"role": "assistant", "content": reply})
        except Exception as e:
            st.error("DeepSeek request failed (see details below).")
            st.exception(e)
