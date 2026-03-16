import os
import tempfile
from datetime import datetime, timedelta
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import bcrypt

from models import db, User, Expense, Task
from record import stt
from model import classify_and_save

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///tracker.db")
# Render uses postgres:// but SQLAlchemy needs postgresql://
if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLALCHEMY_DATABASE_URI"].replace(
        "postgres://", "postgresql://", 1
    )
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=30)
app.config["REMEMBER_COOKIE_SECURE"] = True
app.config["REMEMBER_COOKIE_HTTPONLY"] = True
app.config["REMEMBER_COOKIE_SAMESITE"] = "Lax"

CORS(app)
db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():
    db.create_all()


# ── Auth routes ──────────────────────────────────────────────

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.", "error")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("register.html")

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "error")
            return render_template("register.html")

        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        user = User(name=name, email=email, password_hash=hashed)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for("index"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
            remember = request.form.get("remember") == "1"
            login_user(user, remember=remember)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")


@app.route("/demo-login")
def demo_login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    user = User.query.filter_by(email="jinamkeniya28@gmail.com").first()
    if not user:
        flash("Demo account not found.", "error")
        return redirect(url_for("login"))

    login_user(user)
    return redirect(url_for("index"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ── Main routes ──────────────────────────────────────────────

def _parse_amount(val):
    try:
        cleaned = "".join(c for c in str(val) if c.isdigit() or c == ".")
        return float(cleaned) if cleaned else 0.0
    except (ValueError, TypeError):
        return 0.0


@app.route("/")
@login_required
def index():
    return render_template("home.html")


@app.route("/expenses")
@login_required
def expenses():
    expense_list = Expense.query.filter_by(user_id=current_user.id).all()

    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    month_start = today.replace(day=1).strftime("%Y-%m-%d")

    expenses_data = []
    for e in expense_list:
        expenses_data.append({
            "id": e.id,
            "date": e.date,
            "amount": e.amount,
            "amount_raw": str(e.amount),
            "reason": e.reason,
            "category": e.category,
        })

    total_all = sum(e["amount"] for e in expenses_data)
    total_week = sum(e["amount"] for e in expenses_data if e["date"] >= week_ago)
    total_month = sum(e["amount"] for e in expenses_data if e["date"] >= month_start)
    total_today = sum(e["amount"] for e in expenses_data if e["date"] == today_str)

    cat_totals = defaultdict(float)
    for e in expenses_data:
        cat_totals[e["category"]] += e["amount"]
    cat_breakdown = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)

    daily_totals = defaultdict(float)
    for e in expenses_data:
        daily_totals[e["date"]] += e["amount"]

    return render_template(
        "expenses.html",
        expenses=expenses_data,
        total_all=total_all,
        total_week=total_week,
        total_month=total_month,
        total_today=total_today,
        cat_breakdown=cat_breakdown,
        daily_totals=dict(daily_totals),
        today=today_str,
    )


@app.route("/tracker")
@login_required
def tracker():
    task_list = Task.query.filter_by(user_id=current_user.id).all()

    tasks = []
    for t in task_list:
        tasks.append({
            "id": t.id,
            "task": t.task,
            "deadline": t.deadline,
            "priority": t.priority,
            "created": t.created,
            "status": t.status,
        })

    today = datetime.now().strftime("%Y-%m-%d")
    total = len(tasks)
    done = sum(1 for t in tasks if t["status"] == "done")
    pending = total - done
    overdue = sum(
        1 for t in tasks
        if t["status"] != "done" and t["deadline"] not in ("none", "") and t["deadline"] < today
    )

    return render_template(
        "tracker.html",
        tasks=tasks,
        total=total,
        done=done,
        pending=pending,
        overdue=overdue,
        today=today,
    )


@app.route("/toggle-task", methods=["POST"])
@login_required
def toggle_task():
    data = request.get_json()
    task_id = data.get("id")

    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        return jsonify({"error": "Task not found"}), 404

    task.status = "done" if task.status != "done" else "pending"
    db.session.commit()

    return jsonify({"status": task.status})


@app.route("/edit-expense", methods=["POST"])
@login_required
def edit_expense():
    data = request.get_json()
    expense_id = data.get("id")

    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first()
    if not expense:
        return jsonify({"error": "Expense not found"}), 404

    if "date" in data:
        expense.date = data["date"]
    if "amount" in data:
        expense.amount = _parse_amount(data["amount"])
    if "reason" in data:
        expense.reason = data["reason"]
    if "category" in data:
        expense.category = data["category"]

    db.session.commit()
    return jsonify({"success": True})


@app.route("/delete-expense", methods=["POST"])
@login_required
def delete_expense():
    data = request.get_json()
    expense_id = data.get("id")

    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first()
    if not expense:
        return jsonify({"error": "Expense not found"}), 404

    db.session.delete(expense)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/edit-task", methods=["POST"])
@login_required
def edit_task():
    data = request.get_json()
    task_id = data.get("id")

    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        return jsonify({"error": "Task not found"}), 404

    if "task" in data:
        task.task = data["task"]
    if "deadline" in data:
        task.deadline = data["deadline"]
    if "priority" in data:
        task.priority = data["priority"]
    if "status" in data:
        task.status = data["status"]

    db.session.commit()
    return jsonify({"success": True})


@app.route("/delete-task", methods=["POST"])
@login_required
def delete_task():
    data = request.get_json()
    task_id = data.get("id")

    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        return jsonify({"error": "Task not found"}), 404

    db.session.delete(task)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/upload-recording", methods=["POST"])
@login_required
def upload_recording():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio = request.files["audio"]

    # Use a temp file — don't persist recordings on server
    tmp = tempfile.NamedTemporaryFile(suffix=".webm", delete=False, dir="/tmp")
    try:
        audio.save(tmp.name)
        tmp.close()

        try:
            transcription = stt(tmp.name)
        except Exception as e:
            return jsonify({
                "error": "Transcription failed. The audio may be too short or unclear. Please record again.",
                "error_type": "transcription",
                "detail": str(e),
            }), 500

        if not transcription or not transcription.strip():
            return jsonify({
                "error": "No speech was detected in the recording. Please try again and speak clearly.",
                "error_type": "empty_transcription",
            }), 400

        try:
            result = classify_and_save(transcription, current_user.id)
        except (ValueError, ConnectionError) as e:
            return jsonify({
                "error": str(e),
                "error_type": "classification",
                "transcription": transcription,
            }), 500
        except Exception as e:
            return jsonify({
                "error": "Something went wrong while classifying. Please try recording again.",
                "error_type": "classification",
                "detail": str(e),
                "transcription": transcription,
            }), 500

        return jsonify({
            "message": "Recording processed",
            "transcription": transcription,
            "classification": result,
        })
    finally:
        os.unlink(tmp.name)


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")
