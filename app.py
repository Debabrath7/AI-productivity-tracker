import streamlit as st
import sqlite3
from sqlite3 import Connection
from datetime import datetime, date
import pandas as pd
import openai
import os
import dateparser

# -----------------------------
# Config & Helpers
# -----------------------------

DB_PATH = "tasks.db"

def get_conn() -> Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(conn: Connection):
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT,
            priority INTEGER DEFAULT 3,
            due_date TEXT,
            completed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()

# AI helper (OpenAI)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

def ai_extract_task(text: str) -> dict:
    """
    Use a simple combination of dateparser + (optional) OpenAI fallback to extract structured fields.
    Returns: dict with title, due_date (ISO str or None), notes
    """
    parsed_date = dateparser.parse(text, settings={"PREFER_DATES_FROM": "future"})
    due_iso = parsed_date.isoformat() if parsed_date else None

    title = text
    notes = ""

    if OPENAI_API_KEY:
        try:
            prompt = f"Extract a short title and up to 5 subtasks from this task request. Return JSON with keys: title, subtasks, notes. Input: {text}"
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.2,
            )
            content = resp["choices"][0]["message"]["content"].strip()
            lines = [l.strip() for l in content.splitlines() if l.strip()]
            if lines:
                title = lines[0][:200]
                notes = "\n".join(lines[1:])
        except Exception as e:
            st.debug(f"AI extract failed: {e}")

    return {"title": title, "due_date": due_iso, "notes": notes}

# -----------------------------
# DB CRUD
# -----------------------------

def add_task(conn: Connection, title, description, category, priority, due_date):
    c = conn.cursor()
    c.execute(
        "INSERT INTO tasks (title, description, category, priority, due_date) VALUES (?, ?, ?, ?, ?)",
        (title, description, category, priority, due_date),
    )
    conn.commit()

def update_task(conn: Connection, task_id, **kwargs):
    c = conn.cursor()
    fields = []
    vals = []
    for k, v in kwargs.items():
        fields.append(f"{k} = ?")
        vals.append(v)
    vals.append(task_id)
    sql = f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?"
    c.execute(sql, vals)
    conn.commit()

def delete_task(conn: Connection, task_id):
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()

def get_tasks(conn: Connection, include_completed=True):
    c = conn.cursor()
    if include_completed:
        c.execute("SELECT * FROM tasks ORDER BY completed, priority, due_date IS NULL, due_date")
    else:
        c.execute("SELECT * FROM tasks WHERE completed = 0 ORDER BY priority, due_date IS NULL, due_date")
    rows = c.fetchall()
    return [dict(r) for r in rows]

# -----------------------------
# UI
# -----------------------------

st.set_page_config(page_title="Lumos AI To-Do", layout="centered")

conn = get_conn()
init_db(conn)

st.title("✨ Lumos — AI To-Do & Productivity")

col1, col2 = st.columns([3, 1])

with col1:
    st.header("Add task")
    raw = st.text_area("Describe a task (natural language)", placeholder="e.g. Submit project report by Friday 5pm, high priority")

    with st.expander("Advanced fields"):
        title_manual = st.text_input("Title (optional)")
        description_manual = st.text_area("Description (optional)")
        category = st.selectbox("Category", ["General", "Work", "Study", "Health", "Personal"])
        priority = st.slider("Priority (1 = high, 5 = low)", 1, 5, 3)
        due_input = st.text_input("Due date (optional - natural language)")

    if st.button("AI Parse & Add"):
        parsed = ai_extract_task(raw if raw else title_manual)
        final_title = title_manual or parsed.get("title") or "Untitled Task"
        parsed_due = parsed.get("due_date")
        due_iso = None
        if due_input.strip():
            p = dateparser.parse(due_input)
            due_iso = p.isoformat() if p else None
        else:
            due_iso = parsed_due

        add_task(conn, final_title, description_manual or parsed.get("notes"), category, priority, due_iso)
        st.success("Task added ✓")

with col2:
    st.header("Quick actions")
    show_completed = st.checkbox("Show completed tasks", value=False)
    if st.button("Clear all completed"):
        rows = get_tasks(conn, include_completed=True)
        for r in rows:
            if r["completed"]:
                delete_task(conn, r["id"])
        st.success("Cleared completed tasks")

st.markdown("---")

# Task list
st.header("Your tasks")
rows = get_tasks(conn, include_completed=True)
if not rows:
    st.info("No tasks yet — add one on the left!")
else:
    for r in rows:
        due = r.get("due_date")
        due_str = (dateparser.parse(due).strftime("%b %d, %Y %I:%M %p") if due else "No due date")
        cols = st.columns([0.06, 0.7, 0.12, 0.12])
        completed = bool(r.get("completed"))
        with cols[0]:
            new_completed = st.checkbox("", value=completed, key=f"c{r['id']}")
            if new_completed != completed:
                update_task(conn, r["id"], completed=1 if new_completed else 0)
                st.experimental_rerun()
        with cols[1]:
            st.markdown(f"**{r['title']}**  \n{r.get('description','')}  \n— *{r.get('category','General')}*  ")
            st.caption(f"Due: {due_str} | Priority: {r.get('priority')} | Created: {r.get('created_at')}")
        with cols[2]:
            if st.button("Edit", key=f"e{r['id']}"):
                with st.form(key=f"form{r['id']}"):
                    t = st.text_input("Title", value=r['title'])
                    d = st.text_area("Description", value=r.get('description') or "")
                    cat = st.selectbox("Category", ["General", "Work", "Study", "Health", "Personal"], index=0)
                    pr = st.slider("Priority", 1, 5, value=r.get('priority') or 3)
                    due = st.text_input("Due date (natural language)", value=r.get('due_date') or "")
                    submitted = st.form_submit_button("Save")
                    if submitted:
                        due_parsed = dateparser.parse(due)
                        due_iso = due_parsed.isoformat() if due_parsed else None
                        update_task(conn, r['id'], title=t, description=d, category=cat, priority=pr, due_date=due_iso)
                        st.success("Updated")
                        st.experimental_rerun()
        with cols[3]:
            if st.button("Delete", key=f"d{r['id']}"):
                delete_task(conn, r['id'])
                st.experimental_rerun()

st.markdown("---")

# Productivity summary
st.header("Daily summary")
all_tasks = get_tasks(conn, include_completed=True)
df = pd.DataFrame(all_tasks)
if not df.empty:
    completed_today = df[df['completed'] == 1]
    st.write(f"Total tasks: {len(df)} — Completed: {len(completed_today)}")
    if OPENAI_API_KEY and st.button("AI: Summarize my progress"):
        prompt = "Summarize this user's completed tasks and give 3 short productivity tips.\n\n"
        prompt += df[df['completed'] == 1].to_json(orient='records')
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.3,
            )
            out = resp['choices'][0]['message']['content']
            st.markdown("**AI Summary:**\n" + out)
        except Exception as e:
            st.error(f"AI summary failed: {e}")
else:
    st.info("No tasks to summarize yet.")

st.markdown("---")
st.caption("Built for Lumos Labs style portfolio — Streamlit + OpenAI + SQLite. Set OPENAI_API_KEY in Render for AI features.")
