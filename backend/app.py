# app.py — XamSetu Backend (Groq AI Edition — FINAL CLEAN)

import os, json
from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, session
from flask_cors import CORS
from werkzeug.utils import secure_filename
from jsondb import JSONDatabase
from groq import Groq
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(ENV_PATH)

print("GROQ KEY LOADED:", bool(os.getenv("GROQ_API_KEY")))

# -------------------------------------------------------
# 📌 PATH SETUP (Define FIRST)
# -------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
UPLOAD_DIR = os.path.join(PROJECT_ROOT, 'uploads')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

for sub in ['exams', 'resumes', 'jds']:
    os.makedirs(os.path.join(UPLOAD_DIR, sub), exist_ok=True)


# -------------------------------------------------------
# 📌 LOAD PREDEFINED QUESTIONS
# -------------------------------------------------------
PREDEFINED_PATH = os.path.join(DATA_DIR, "predefined_questions.json")

if os.path.exists(PREDEFINED_PATH):
    with open(PREDEFINED_PATH, "r", encoding="utf-8") as f:
        PREDEFINED_QNA = json.load(f)
else:
    PREDEFINED_QNA = []


# -------------------------------------------------------
# 🚀 GROQ AI SETUP (SECURE)
# -------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError("❌ GROQ_API_KEY not found. Check your .env file")

groq_client = Groq(api_key=GROQ_API_KEY)

MODEL_NAME = "llama3-70b-8192"


def generate_ai_reply(message):
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are XamBot, an AI mentor for students and job seekers. "
                        "Be helpful, concise, and professional."
                    )
                },
                {"role": "user", "content": message}
            ],
            max_tokens=300,
            temperature=0.4
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("❌ GROQ ERROR:", e)
        return "⚠️ AI error. Please try again later."

# -------------------------------------------------------
# 🎯 FLASK APP
# -------------------------------------------------------
app = Flask(
    __name__,
    template_folder=os.path.join(PROJECT_ROOT, "templates"),
    static_folder=os.path.join(PROJECT_ROOT, "static")
)

app.secret_key = "xamsetu_super_secure_secret_key_987654"
CORS(app)

db = JSONDatabase(DATA_DIR)


# -------------------------------------------------------
# 🔍 Skill Extractor
# -------------------------------------------------------
COMMON_SKILLS = [
    "Python", "SQL", "Excel", "Tableau",
    "JavaScript", "HTML", "CSS", "React",
    "TensorFlow", "PyTorch", "Linux", "Docker",
    "Kubernetes", "AWS"
]

def extract_skills(text):
    text = text.lower()
    return [s for s in COMMON_SKILLS if s.lower() in text]


# -------------------------------------------------------
# 📁 Ensure Default JSON Data Exists
# -------------------------------------------------------
def ensure_json_files():
    initial_files = {
        "users": [
            {"id": 1, "username": "demo", "password": "demo", "role": "student"}
        ],
        "jobs": [
            {"id": 1, "title": "Data Analyst", "skills": ["Python", "SQL", "Excel", "Tableau"]},
            {"id": 2, "title": "Web Developer", "skills": ["HTML", "CSS", "JavaScript", "React"]},
            {"id": 3, "title": "ML Engineer", "skills": ["Python", "TensorFlow", "PyTorch"]}
        ],
        "exams": [
            {"id": 1, "title": "Python Basics Test", "skills": ["Python"]},
            {"id": 2, "title": "SQL Fundamentals", "skills": ["SQL"]}
        ],
        "resources": [
            {"id": 1, "title": "FreeCodeCamp - Python", "url": "https://www.freecodecamp.org/learn/"},
            {"id": 2, "title": "Kaggle - SQL Course", "url": "https://www.kaggle.com/learn/intro-to-sql"}
        ],
        "chat_logs": []
    }

    for name, content in initial_files.items():
        path = os.path.join(DATA_DIR, f"{name}.json")
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump(content, f, indent=2)

ensure_json_files()


# -------------------------------------------------------
# 🌐 HTML ROUTES
# -------------------------------------------------------
@app.route("/")
def index():
    return render_template("XamSetu.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/registration")
def registration_page():
    return render_template("registration.html")

@app.route("/chat")
def chat_page():
    return render_template("chat.html")

@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")

@app.route("/upload")
def upload_page():
    return render_template("upload.html")


@app.route("/resources")
def resources_page():
    return render_template("resources.html", resources=db.find_all("resources"))


# -------------------------------------------------------
# 📂 Serve Uploaded Files
# -------------------------------------------------------
@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)


# -------------------------------------------------------
# 📝 REGISTRATION API
# -------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.json or {}

    required = ["full_name", "phone", "email", "occupation", "password"]
    if not all(data.get(k, "").strip() for k in required):
        return jsonify({"ok": False, "error": "All fields are required!"}), 400

    if db.find_one("users", lambda u: u.get("email") == data["email"]):
        return jsonify({"ok": False, "error": "Email already registered!"}), 400

    new_id = len(db.find_all("users")) + 1

    user = db.insert("users", {
        "id": new_id,
        **data
    })

    return jsonify({"ok": True, "user": user})


# -------------------------------------------------------
# 🔐 LOGIN API
# -------------------------------------------------------
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json or {}

    identifier = data.get("identifier")
    password = data.get("password")

    user = db.find_one(
        "users",
        lambda u:
            (u.get("email") == identifier or u.get("phone") == identifier) and
            u.get("password") == password
    )

    if not user:
        return jsonify({"ok": False, "error": "Invalid login credentials"}), 401

    session["user_id"] = user["id"]

    return jsonify({"ok": True, "user": user})


# -------------------------------------------------------
# 🚪 LOGOUT
# -------------------------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# -------------------------------------------------------
# 👤 USER DASHBOARD
# -------------------------------------------------------
@app.route("/user_dashboard")
def user_dashboard():
    user_id = session.get("user_id")

    if not user_id:
        return redirect("/login")

    user = db.find_one("users", lambda u: u["id"] == user_id)

    return render_template("user_dashboard.html", user=user)


# -------------------------------------------------------
# 📤 FILE UPLOAD
# -------------------------------------------------------
def save_uploaded_file(file, subfolder):
    filename = secure_filename(file.filename)
    dest_folder = os.path.join(UPLOAD_DIR, subfolder)

    path = os.path.join(dest_folder, filename)
    base, ext = os.path.splitext(filename)

    count = 1
    while os.path.exists(path):
        filename = f"{base}_{count}{ext}"
        path = os.path.join(dest_folder, filename)
        count += 1

    file.save(path)
    return os.path.join(subfolder, filename)


@app.route("/api/upload", methods=["POST"])
def api_upload():
    file = request.files.get("file")
    ftype = request.form.get("type", "exam")

    mapping = {"exam": "exams", "resume": "resumes", "jd": "jds"}

    if not file or ftype not in mapping:
        return jsonify({"ok": False, "error": "Invalid upload"}), 400

    saved_path = save_uploaded_file(file, mapping[ftype])
    db.insert(mapping[ftype], {"file_path": saved_path})

    return jsonify({"ok": True, "path": saved_path})


# -------------------------------------------------------
# 🤖 CHAT API — Predefined + Smart + AI
# -------------------------------------------------------
@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.json or {}
    message = data.get("message", "").strip().lower()

    if not message:
        return jsonify({"ok": False, "error": "Empty message"}), 400

    # 1️⃣ Predefined Question Match (Exact + Partial)
    for qa in PREDEFINED_QNA:
        if qa["question"].lower().strip() in message:
            return jsonify({"ok": True, "reply": qa["answer"]})

    # 2️⃣ Smart Job Matcher
    if ("job" in message and "can" in message) or ("what job" in message):
        skills = extract_skills(message)
        if not skills:
            return jsonify({"ok": True, "reply": "Tell me your skills (Example: Python, SQL, Excel)."})
        
        results = []
        for job in db.find_all("jobs"):
            required = job["skills"]
            matched = [s for s in required if s in skills]
            score = int((len(matched) / len(required)) * 100)
            results.append(f"{job['title']} — {score}% match")

        return jsonify({"ok": True, "reply": "\n".join(results)})

    # 3️⃣ AI Fallback
    reply = generate_ai_reply(message)
    return jsonify({"ok": True, "reply": reply})


# -------------------------------------------------------
# 🚀 RUN SERVER
# -------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
