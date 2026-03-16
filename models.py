from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    expenses = db.relationship("Expense", backref="user", lazy=True)
    tasks = db.relationship("Task", backref="user", lazy=True)
    notes = db.relationship("Note", backref="user", lazy=True)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    reason = db.Column(db.String(200), nullable=False, default="")
    category = db.Column(db.String(20), nullable=False, default="other")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    task = db.Column(db.String(300), nullable=False)
    deadline = db.Column(db.String(10), nullable=False, default="none")
    priority = db.Column(db.String(10), nullable=False, default="medium")
    created = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(10), nullable=False, default="pending")


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False, default="")
    content = db.Column(db.Text, nullable=False, default="")
    category = db.Column(db.String(20), nullable=False, default="other")
    is_pinned = db.Column(db.Boolean, nullable=False, default=False)
    created = db.Column(db.String(10), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
