import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from together import Together
from datetime import datetime
from gtts import gTTS
from tempfile import NamedTemporaryFile
import fitz  # PyMuPDF
import csv
import os

# 🔐 API Setup
st.set_page_config(page_title="AI-powered HR Assistant", layout="centered")
TOGETHER_API_KEY = st.secrets["TOGETHER_API_KEY"]
client = Together(api_key=TOGETHER_API_KEY)
model = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"

# 📘 HR Knowledge Base
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
"""

# 🧠 Mood detection logic
def detect_mood(text):
    text = text.lower()
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
    "stress": "I'm really sorry you're feeling stressed. You're not alone. Take a short break, breathe deeply, or speak with someone. HR is here to support you ❤️",
    "anxiety": "Anxiety can be really tough. Take it slow and be kind to yourself. You're doing your best.",
    "sad": "I'm sorry you're feeling this way. It's okay to not be okay sometimes. You're valued here.",
    "tired": "Sounds like you've been working hard. Make sure you're resting enough — rest is productive too.",
}

def is_checkin_request(text):
    checkin_keywords = [
        "check in", "check-in", "how am i doing", "not feeling good",
        "motivate me", "motivation", "i’m unproductive", "i feel off"
    ]
    text = text.lower()
    return any(phrase in text for phrase in checkin_keywords)

def log_mood_to_csv(mood_score):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("mood_log.csv", mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, mood_score])

# 🌟 UI Start
if "history" not in st.session_state:
    st.session_state.history = []

st.title("👩‍💼 AI-powered HR Assistant")
st.write("Ask me anything about your job, leave policy, resume, or mood check-in.")

# 📄 Resume upload
st.markdown("### 📎 Upload Your Resume (Optional)")
resume_file = st.file_uploader("Upload your resume (PDF or .txt)", type=["pdf", "txt"])
resume_text = ""
if resume_file:
    if resume_file.type == "application/pdf":
        doc = fitz.open(stream=resume_file.read(), filetype="pdf")
        for page in doc:
            resume_text += page.get_text()
    elif resume_file.type == "text/plain":
        resume_text = resume_file.read().decode("utf-8")
    st.success("Resume uploaded successfully!")

# 💬 User input
user_input = st.text_input("👤 You:")

if st.button("Send") and user_input:
    detected_mood = detect_mood(user_input)

    if detected_mood:
        reply = mood_responses[detected_mood]
        st.session_state.history.append((user_input, reply))

    elif is_checkin_request(user_input):
        st.session_state.history.append((user_input, "Sure! On a scale of 1–10, how are you feeling today?"))
        mood_score = st.number_input("Your mood (1 = bad, 10 = amazing):", min_value=1, max_value=10, step=1)
        if st.button("Submit Mood"):
            if mood_score <= 5:
                reply = "I'm really sorry you're feeling that way. Take it easy on yourself — HR is always here to support you ❤️"
            elif 6 <= mood_score <= 7:
                reply = "You're doing better than you think. Keep going. 💪"
            else:
                reply = "You're crushing it! Keep the energy high and share the vibe! 🚀"
            log_mood_to_csv(mood_score)
            st.session_state.history.append((f"Mood: {mood_score}", reply))

    else:
        messages = [{
            "role": "system",
            "content": f"You are a friendly, professional HR assistant. Only refer to HR policies below:\n\n{HR_KNOWLEDGE}"
        }]
        for q, a in st.session_state.history:
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": a})

        if "resume" in user_input.lower() and resume_text:
            user_input += f"\n\nHere is my resume:\n{resume_text[:2000]}"

        messages.append({"role": "user", "content": user_input})

        with st.spinner("Konan is typing..."):
            response = client.chat.completions.create(model=model, messages=messages)
            reply = response.choices[0].message.content.strip()
            st.session_state.history.append((user_input, reply))

    # 📝 Display chat
    for q, a in st.session_state.history:
        st.markdown(f"**👤 You:** {q}")
        st.markdown(f"**🤖 Konan:** {a}")

    # 🔊 Text-to-Speech
    with NamedTemporaryFile(delete=True) as fp:
        tts = gTTS(text=reply)
        tts.save(fp.name + ".mp3")
        st.audio(fp.name + ".mp3", format="audio/mp3")

# 📈 Mood Trend Chart
if os.path.exists("mood_log.csv"):
    st.markdown("### 📈 Your Mood Trend")
    mood_df = pd.read_csv("mood_log.csv", names=["Timestamp", "Mood"])
    mood_df["Timestamp"] = pd.to_datetime(mood_df["Timestamp"])
    fig, ax = plt.subplots()
    ax.plot(mood_df["Timestamp"], mood_df["Mood"], marker='o', linestyle='-')
    ax.set_title("Mood Over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Mood (1-10)")
    plt.xticks(rotation=45)
    st.pyplot(fig)
