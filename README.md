# Virtual-HR-assistance 🧑‍💼💬

A friendly, AI-powered virtual HR assistant built with **Streamlit** and **Together AI's LLaMA model**. This app allows employees to:

- ✅ Chat with a smart HR assistant
- 📄 Upload resumes for instant feedback
- 😌 Do daily mood check-ins
- 📈 Visualize mood trends over time
- 🧠 Ask questions about HR policies
- 🔊 Get responses with text-to-speech

---

## 🚀 Features

| Feature | Description |
|--------|-------------|
| 💬 Natural Chat | Smart, context-aware replies from LLaMA |
| 📄 Resume Review | Upload PDF or .txt resume and get instant feedback |
| 😌 Mood Check-in | Type "I'm stressed" or "motivate me" for mental health support |
| 📈 Mood Chart | View mood trends over time with a line chart |
| 🔊 Audio Reply | Konan speaks using gTTS (Google Text-to-Speech) |

---

## 🛠 How to Run Locally

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/konan-hr-assistant.git
cd konan-hr-assistant
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Add your Together AI API key
Create a file `.streamlit/secrets.toml`:
```toml
TOGETHER_API_KEY = "your_api_key_here"
```

### 4. Run the app
```bash
streamlit run app.py
```

---

## 🗂 Project Structure
```
konan_hr_assistant/
├── app.py                         # Main entry point
├── components/
│   └── conversation_flow.py      # Core assistant logic
├── mood_log.csv                  # Auto-generated mood logs
├── requirements.txt              # All Python dependencies
└── .streamlit/
    └── secrets.toml              # API keys
```

---

## ✨ Upcoming Ideas
- Anonymous feedback logging
- Job-role-based onboarding tips
- Weekly mood trend emails
- Multi-language support

---

## 👥 Made By
**Konan AI Labs** – On a mission to humanize HR with helpful, always-there assistants ❤️

