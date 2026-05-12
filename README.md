<div align="center">
  <h1>🧠 Digital Twin — AI Doppelganger</h1>
  <p><strong>Your Personal AI Clone. It thinks like you, talks like you, and acts like you.</strong></p>
  
  <a href="https://digital-twin-jqav.onrender.com"><strong>🔴 View Live Demo</strong></a>
  <br><br>
  
  ![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)
  ![Django](https://img.shields.io/badge/Django-6.x-092E20?style=for-the-badge&logo=django&logoColor=green)
  ![JavaScript](https://img.shields.io/badge/JavaScript-ES6-323330?style=for-the-badge&logo=javascript&logoColor=F7DF1E)
  ![Groq API](https://img.shields.io/badge/Groq_API-F55036?style=for-the-badge)
  ![Llama-3](https://img.shields.io/badge/Llama_3.3_70B-0466c8?style=for-the-badge)
</div>

---

## 📖 Overview

**Digital Twin** is a highly personalized, AI-driven web application designed to act as your virtual surrogate. Instead of interacting with a generic, polite AI assistant, you converse with an AI that has been specifically configured to mimic *your* exact personality, daily habits, and current mood.

Whether you are a late-night coder, a procrastinating student, or a highly focused developer, the AI adapts its tone, reasoning, and vocabulary (including raw Hinglish slang) to mirror how *you* would genuinely react to real-world scenarios.

---

## ✨ Key Features

* 🎭 **Deep Personality Cloning:** Define your profile by inputting your sleep cycles, dietary preferences, core personality traits, and current life phase. The AI integrates these directly into its cognitive prompt.
* ⚡ **Context-Aware Predictions:** Ask your Twin how it would handle a situation. It actively factors in the actual real-world time and your current emotional state (Chill, Stressed, Motivated) to deliver customized, brutally honest predictions.
* 🔥 **Dynamic Roast-o-Meter:** A custom-built frontend algorithm analyzes the savageness of the AI's response in real-time, displaying a dynamic visual meter ranging from *Chill 😊* to *Brutal Destruction 🌋*.
* ⚔️ **AI vs AI Debate Mode:** Pit your Digital Twin against predefined personas (e.g., a Strict B.Tech Professor, Shahrukh Khan, or Sharma Ji). Watch a fully autonomous, 4-turn conversational debate unfold automatically on the dashboard.
* 🎵 **Dynamic Spotify Integration:** The UI seamlessly embeds official Spotify playlists that dynamically change tracks to match your Twin's active mood.
* 🌗 **Modern UI/UX:** A fully responsive, modern dashboard featuring Light/Dark mode toggles, interactive status chips, and real-time typing indicators without page reloads (AJAX).
* 🧠 **Memory & History Logging:** The app tracks your past scenarios and choices, storing them securely so you can review how your AI Twin's decision-making evolves.

---

## 🛠️ Tech Stack

* **Backend:** Python, Django 6.0.4
* **Frontend:** HTML5, CSS3 (Custom Variables, Flexbox/Grid), Vanilla JavaScript (Fetch API/AJAX)
* **AI Engine:** Groq API (`llama-3.3-70b-versatile` model for ultra-low latency inference)
* **Database:** SQLite (Local Development) / PostgreSQL (Production)
* **Deployment:** Render, Gunicorn, Whitenoise (for Static File Management)

---

## 📁 Project Structure

```text
Digital-Twin/
│
├── digital_twin_pro/         # Main Django Project Settings
│   ├── settings.py           # Configured with Whitenoise & Static roots
│   ├── urls.py               # Global routing
│   └── wsgi.py               # Production entry point
│
├── twin_engine/              # Core Application
│   ├── logic.py              # 🧠 AI Logic, Prompt Engineering & Groq API Calls
│   ├── models.py             # Database Schemas (User Preferences, Settings, History)
│   ├── views.py              # Controllers & AJAX Endpoint Handlers
│   ├── urls.py               # App-level routing
│   └── templates/
│       └── twin_dashboard.html  # Main Frontend UI (Single Page App style)
│
├── .env                      # Environment Variables (Ignored in Git)
├── requirements.txt          # Python dependencies
├── build.sh                  # Render deployment script
└── manage.py                 # Django CLI
```

---

## 🚀 Installation & Local Setup

Follow these steps to run the Digital Twin on your local machine.

### 1. Clone the Repository

```bash
git clone https://github.com/ajay160380/Digital-Twin.git
cd Digital-Twin
```

### 2. Create and Activate a Virtual Environment

```bash
python -m venv env
```

```bash
# On macOS/Linux:
source env/bin/activate

# On Windows:
env\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables

Create a `.env` file in the root directory (where `manage.py` is located) and add your Groq API key:

```env
GROQ_API_KEY=gsk_your_actual_api_key_here
```

> You can get a free API key from [Groq Console](https://console.groq.com/keys)

### 5. Apply Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create a Superuser *(Optional but recommended)*

```bash
python manage.py createsuperuser
```

### 7. Run the Development Server

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000` in your web browser.

---

## ⚙️ How The AI Engine Works

The core intelligence of this app resides in `twin_engine/logic.py`.

1. **Context Assembly:** When a user submits a scenario, the backend fetches their database profile, current time, and mood.
2. **Dynamic Prompting:** A highly specific `system_prompt` is generated. It strictly commands the LLM to drop its generic AI persona, adopt the exact traits of the user, and respond using conversational constraints (e.g., maximum 6 lines, no bullet points, raw Hinglish).
3. **Inference:** The prompt is sent to Groq's `llama-3.3-70b-versatile` model. Exponential backoff retries are implemented to gracefully handle API rate limits.
4. **Data Parsing:** The result is returned to the frontend where vanilla JavaScript parses the JSON and dynamically updates the DOM.

---

## 👨‍💻 Team & Contributors

* **Ajay Vishwakarma** — Lead Backend Developer & AI Integrator
* **Manyata Gupta** — Co-Developer & UI/UX Contributor
