"""One-time script to migrate existing CSV data into the database.

Usage:
    1. First register a user account via the web app
    2. Run: python migrate_csv.py <user_email>

This will import all expenses and tasks from data/expenses.csv and data/tasks.csv
into the database, associated with the specified user.
"""

import sys
import os
import csv

os.environ.setdefault("DATABASE_URL", "sqlite:///tracker.db")

from app import app
from models import db, User, Expense, Task

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPENSES_CSV = os.path.join(BASE_DIR, "data", "expenses.csv")
TASKS_CSV = os.path.join(BASE_DIR, "data", "tasks.csv")


def migrate(email):
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"Error: No user found with email '{email}'")
            print("Register an account first, then run this script.")
            sys.exit(1)

        # Migrate expenses
        if os.path.exists(EXPENSES_CSV):
            with open(EXPENSES_CSV, "r") as f:
                reader = csv.reader(f)
                rows = list(reader)
            if len(rows) > 1:
                for row in rows[1:]:
                    try:
                        amount = float("".join(c for c in str(row[1]) if c.isdigit() or c == ".") or "0")
                    except (ValueError, IndexError):
                        amount = 0.0
                    expense = Expense(
                        user_id=user.id,
                        date=row[0] if len(row) > 0 else "",
                        amount=amount,
                        reason=row[2] if len(row) > 2 else "",
                        category=row[3] if len(row) > 3 else "other",
                    )
                    db.session.add(expense)
                print(f"Imported {len(rows) - 1} expenses.")
            else:
                print("No expense data to import.")
        else:
            print("No expenses.csv found.")

        # Migrate tasks
        if os.path.exists(TASKS_CSV):
            with open(TASKS_CSV, "r") as f:
                reader = csv.reader(f)
                rows = list(reader)
            if len(rows) > 1:
                for row in rows[1:]:
                    task = Task(
                        user_id=user.id,
                        task=row[0] if len(row) > 0 else "",
                        deadline=row[1] if len(row) > 1 else "none",
                        priority=row[2] if len(row) > 2 else "medium",
                        created=row[3] if len(row) > 3 else "",
                        status=row[4] if len(row) > 4 else "pending",
                    )
                    db.session.add(task)
                print(f"Imported {len(rows) - 1} tasks.")
            else:
                print("No task data to import.")
        else:
            print("No tasks.csv found.")

        db.session.commit()
        print(f"Migration complete for user: {user.name} ({user.email})")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python migrate_csv.py <user_email>")
        sys.exit(1)
    migrate(sys.argv[1])
