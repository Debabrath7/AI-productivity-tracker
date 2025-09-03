import streamlit as st
import sqlite3
import os
from datetime import datetime
import dateparser
from openai import OpenAI

# ----------------------------
# Database Setup
# ----------------------------
DB_FILE = "tasks.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            due_date TEXT,
            priority TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    conn.commit()
    conn.close()

def add_task(title, due_date=None, priority="medium"):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO tasks (title, due_date, priority) VALUES (?, ?, ?)",
              (title, due_date, priority))
    conn.commit()
    conn.close()

def get_tasks():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM tasks ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def update_task_status(task_id, status):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

# ----------------------------
# OpenAI Setup
# ----------------------------
client = None
if os.getenv("OPENAI_API_KEY"):
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    except Exception as e:
        st.error(f"OpenAI init failed: {e}")

# ----------------------------
# AI Helpers
# ----------------------------
def ai_extract_task(raw_text):
    """Extracts structured task info using AI, with fallback."""
    try:
        if not client:
            return {"title": raw_text, "due_date": None, "priority": "medium"}

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "system",
                "content": "You are a helpful assistant that extracts task details (title, due_date, priority)."
            }, {
                "role": "user",
                "content": raw_text
            }]
        )
        ai_text = response.choices[0].message.content

        # Very basic parsing (could be improved with JSON schema)
        due_date = dateparser.parse(ai_text)
        return {
            "title": raw_text,
            "due_date": due_date.strftime("%Y-%m-%d") if due_date else None,
            "priority": "medium"
        }
    except Exception as e:
        st.error(f"AI extract failed: {e}")
        return {"title": raw_text, "due_date": None, "priority": "medium"}

def ai_generate_subtasks(title):
    try:
        if not client:
            return ["(AI features disabled)"]
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "system",
                "content": "Break down the given task into 3-5 subtasks."
            }, {
                "role": "user",
                "content": title
            }]
        )
        return response.choices[0].message.content.split("\n")
    except Exception as e:
        st.error(f"AI subtasks failed: {e}")
        return ["(error generating subtasks)"]

def ai_daily_summary(tasks):
    try:
        if not client:
            return "AI summary disabled."
        task_list = "\n".join([f"- {t[1]} ({t[4]})" for t in tasks])
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "system",
                "content": "Summarize today's tasks briefly."
            }, {
                "role": "user",
                "content": task_list
            }]
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"AI summary failed: {e}")
        return "Error generating summary."

# ----------------------------
# Streamlit UI
# ----------------------------
st.set_page_config(page_title="AI Productivity Tracker", layout="centered")
st.title("AI Productivity Tracker")

init_db()

# Add Task Section
st.header("➕ Add a Task")
with st.form("task_form"):
    raw = st.text_input("Enter your task (AI will parse if possible):")
    title_manual = st.text_input("Or enter task title manually:")
    due_date_manual = st.date_input("Due Date (optional)", value=None)
    priority_manual = st.selectbox("Priority", ["low", "medium", "high"])
    submitted = st.form_submit_button("Add Task")

    if submitted:
        if raw or title_manual:
            parsed = ai_extract_task(raw if raw else title_manual)
            title = parsed["title"] if parsed else title_manual
            due = parsed["due_date"] or (due_date_manual.strftime("%Y-%m-%d") if due_date_manual else None)
            priority = parsed["priority"] or priority_manual
            add_task(title, due, priority)
            st.success(f"Task added: {title}")
            st.experimental_rerun()
        else:
            st.warning("Please enter a task.")

# Task List
st.header("Your Tasks")
tasks = get_tasks()
if tasks:
    for t in tasks:
        task_id, title, due_date, priority, status = t
        cols = st.columns([4, 2, 2, 2])
        cols[0].write(f"**{title}** (Due: {due_date if due_date else 'N/A'})")
        if cols[1].button("Done", key=f"done_{task_id}"):
            update_task_status(task_id, "done")
            st.experimental_rerun()
        if cols[2].button("🗑Delete", key=f"del_{task_id}"):
            delete_task(task_id)
            st.experimental_rerun()
        if cols[3].button("Subtasks", key=f"sub_{task_id}"):
            st.write(ai_generate_subtasks(title))
else:
    st.info("No tasks yet. Add one above!")

# Daily Summary
st.header("Daily Summary")
if tasks:
    st.write(ai_daily_summary(tasks))
else:
    st.write("No tasks yet to summarize.")
