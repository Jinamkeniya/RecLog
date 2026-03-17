import os
import json
from datetime import datetime

from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a smart assistant that classifies and extracts structured data from voice transcriptions.

The transcription will be in English, Hindi, or Hinglish (a mix of both). Regardless of the input language, you must always respond with field values in English.

The transcription may contain numbers spoken in Hindi words. You MUST convert all Hindi number words to their numeric digits. Examples:
- "do sau" or "दो सौ" = 200
- "pachaas" or "पचास" = 50
- "dedh hazaar" or "डेढ़ हज़ार" = 1500
- "saadhe teen sau" or "साढ़े तीन सौ" = 350
- "paanch sau pachaas" or "पांच सौ पचास" = 550
- "hazaar" or "हज़ार" = 1000
- "das hazaar" or "दस हज़ार" = 10000
Always output the final numeric value as a number, never as Hindi words.

Given a transcribed text, you must:
1. Classify it as either "expense" or "task".
   - "expense": anything related to spending money, buying something, paying for something, costs, bills, etc.
   - "task": anything related to planning, to-dos, reminders, deadlines, goals, scheduling, etc.

2. Extract structured fields based on the category:

   If "expense":
   - "date": the date mentioned in the text, in YYYY-MM-DD format. If no date is mentioned, use "today".
   - "amount": the monetary amount as a number (no currency symbols). If unclear, use "0".
   - "reason": a short description of what the money was spent on.
   - "expense_category": classify the expense into one of these categories: "food", "groceries", "transport", "shopping", "bills", "entertainment", "health", "education", or "other".
     - Use "groceries" for grocery shopping, supermarket purchases, vegetables, fruits, household supplies, and daily essentials.
     - Use "food" for restaurants, dining out, snacks, takeout, and ready-to-eat meals.
     - Use "shopping" for clothing, electronics, gadgets, and non-grocery retail purchases.

   If "task":
   - "task": a concise description of the task or plan.
   - "deadline": the deadline or due date mentioned, in YYYY-MM-DD format. If only a day name is given (e.g. "Monday"), calculate the next occurrence. If "today" is mentioned, use today's date. If no deadline is mentioned, use "none".
   - "priority": estimate priority as "high", "medium", or "low" based on urgency cues in the text.

You MUST respond with valid JSON only, no extra text. Use this exact format:

For expenses:
{"category": "expense", "date": "...", "amount": "...", "reason": "...", "expense_category": "..."}

For tasks:
{"category": "task", "task": "...", "deadline": "...", "priority": "..."}
"""

MAX_RETRIES = 2


def _extract_json(raw):
    """Try to extract valid JSON from the model's response, even if it's wrapped in extra text."""
    raw = raw.strip()

    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        raw = "\n".join(lines).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            pass

    return None


def classify_and_save(transcription, user_id):
    """Classify transcribed text and save structured data to the database."""
    from models import db, Expense, Task

    if not transcription or not transcription.strip():
        raise ValueError("Empty transcription — no speech was detected. Please record again.")

    last_error = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": transcription},
                ],
                response_format={"type": "json_object"},
            )
        except Exception as e:
            raise ConnectionError(f"Could not reach the language model: {e}")

        raw = response.choices[0].message.content
        result = _extract_json(raw)

        if result is None:
            last_error = f"Model returned invalid response (attempt {attempt + 1}): {raw[:200]}"
            continue

        category = result.get("category", "").lower()

        if category not in ("expense", "task"):
            last_error = f"Model returned unknown category '{category}' (attempt {attempt + 1})"
            continue

        today = datetime.now().strftime("%Y-%m-%d")

        if category == "expense":
            date = result.get("date", today)
            if date.lower() == "today":
                date = today
            amount = result.get("amount", "0")
            try:
                amount = float(str(amount).replace(",", ""))
            except (ValueError, TypeError):
                amount = 0.0
            reason = result.get("reason", "")
            expense_cat = result.get("expense_category", "other").lower()
            valid_cats = ("food", "groceries", "transport", "shopping", "bills", "entertainment", "health", "education", "other")
            if expense_cat not in valid_cats:
                expense_cat = "other"

            expense = Expense(
                user_id=user_id,
                date=date,
                amount=amount,
                reason=reason,
                category=expense_cat,
            )
            db.session.add(expense)
            db.session.commit()

            result["id"] = expense.id
            result["date"] = date
            result["amount"] = str(amount)
            result["expense_category"] = expense_cat

        elif category == "task":
            task_text = result.get("task", "")
            deadline = result.get("deadline", "none")
            if deadline.lower() == "today":
                deadline = today
            priority = result.get("priority", "medium").lower()
            if priority not in ("high", "medium", "low"):
                priority = "medium"

            task = Task(
                user_id=user_id,
                task=task_text,
                deadline=deadline,
                priority=priority,
                created=today,
                status="pending",
            )
            db.session.add(task)
            db.session.commit()

            result["id"] = task.id
            result["deadline"] = deadline
            result["priority"] = priority
            result["created"] = today
            result["status"] = "pending"

        return result

    raise ValueError(last_error or "Classification failed after multiple attempts. Please try recording again.")


INSIGHTS_PROMPT = """You are a personal finance analyst. You will be given a user's expense data from the last 30 days as a JSON array.

Analyze the data and provide a short, actionable insights report. Be specific with numbers and percentages. Write in a friendly, conversational tone as if you're a smart financial buddy.

Structure your response as a short report with these sections (use markdown):

**Summary** — One sentence overview of total spending and number of transactions.

**Top Categories** — Which categories they spent the most on, with amounts and percentages.

**Trends** — Any patterns you notice (e.g. spending spikes on certain days, weekend vs weekday, increasing/decreasing trend).

**Tips** — 2-3 specific, actionable suggestions to save money based on their actual data.

Keep it concise — aim for 150-250 words total. Do NOT use any JSON in your response. Use rupee symbol (₹) for amounts."""


def generate_insights(expenses_data):
    """Generate AI-powered spending insights from the last 30 days of expenses."""
    if not expenses_data:
        return "No expense data available for the last 30 days. Start recording your expenses to get personalized insights!"

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": INSIGHTS_PROMPT},
                {"role": "user", "content": json.dumps(expenses_data)},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise ConnectionError(f"Could not generate insights: {e}")
