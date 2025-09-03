import streamlit as st
import sqlite3
from sqlite3 import Connection
from datetime import datetime, date, timedelta
import dateparser
import pandas as pd
import os

# -----------------------------
# Config
# -----------------------------
DB_PATH = "tasks.db"
st.set_page_config(page_title="Lumos — Smooth To-Do", layout="centered", page_icon="")

# -----------------------------
# DB helpers
# -----------------------------
def get_conn() -> Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT,
            priority INTEGER DEFAULT 3,    -- 1 = high, 5 = low
            due_date TEXT,
            completed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT
        );
        """
    )
    conn.commit()
    conn.close()

def add_task(title, description=None, category="Other", priority=3, due_date=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO tasks (title, description, category, priority, due_date) VALUES (?, ?, ?, ?, ?)",
        (title, description, category, priority, due_date),
    )
    conn.commit()
    conn.close()

def update_task(task_id, **kwargs):
    conn = get_conn()
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
    conn.close()

def delete_task(task_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

def fetch_tasks(filter_by="all", sort_by="created_desc"):
    conn = get_conn()
    c = conn.cursor()
    base = "SELECT * FROM tasks"
    if filter_by == "pending":
        base += " WHERE completed = 0"
    elif filter_by == "done":
        base += " WHERE completed = 1"
    # sorting
    if sort_by == "due_asc":
        base += " ORDER BY due_date IS NULL, due_date ASC"
    elif sort_by == "priority_asc":
        base += " ORDER BY priority ASC"
    elif sort_by == "created_asc":
        base += " ORDER BY created_at ASC"
    else:
        base += " ORDER BY created_at DESC"
    c.execute(base)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# -----------------------------
# Utilities / Features
# -----------------------------
KEYWORDS_TO_CATEGORY = {
    "work": ["report", "meeting", "client", "deploy", "debug", "presentation", "email"],
    "study": ["study", "revise", "exam", "assignment", "homework", "read", "practice"],
    "health": ["doctor", "exercise", "gym", "run", "walk", "yoga", "meditate", "sleep"],
    "personal": ["buy", "call", "reminder", "birthday", "pay", "invoice", "plan", "travel"],
}

def auto_categorize(text: str):
    txt = (text or "").lower()
    for cat, keywords in KEYWORDS_TO_CATEGORY.items():
        for kw in keywords:
            if kw in txt:
                return cat.capitalize()
    return "Other"

def parse_due_date(text: str):
    if not text:
        return None
    dt = dateparser.parse(text, settings={"PREFER_DATES_FROM": "future"})
    return dt.isoformat() if dt else None

def format_due(due_iso):
    if not due_iso:
        return "No due date"
    try:
        dt = dateparser.parse(due_iso)
        return dt.strftime("%b %d, %Y %I:%M %p")
    except:
        return due_iso

def priority_badge(priority: int):
    # priority 1 -> High (red), 2-3 -> medium (orange), 4-5 -> low (green)
    if priority <= 1:
        color = "#e11d48"  # red
        text = "High"
    elif priority <= 3:
        color = "#f59e0b"  # orange
        text = "Medium"
    else:
        color = "#10b981"  # green
        text = "Low"
    badge_html = f"""<span style="background:{color}; color:white; padding:4px 8px; border-radius:12px; font-size:12px;">{text}</span>"""
    return badge_html

def is_overdue(due_iso):
    if not due_iso:
        return False
    try:
        dt = dateparser.parse(due_iso)
        return dt.date() < date.today()
    except:
        return False

def calc_progress(tasks):
    if not tasks:
        return 0
    total = len(tasks)
    done = sum(1 for t in tasks if t.get("completed"))
    return int(done / total * 100)

def calc_streak():
    # Count consecutive days up to today with at least one completed task
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT DISTINCT date(completed_at) as d FROM tasks WHERE completed = 1 AND completed_at IS NOT NULL")
    rows = c.fetchall()
    conn.close()
    completed_dates = set()
    for r in rows:
        if r["d"]:
            try:
                completed_dates.add(datetime.strptime(r["d"], "%Y-%m-%d").date())
            except:
                # handle if time included
                try:
                    completed_dates.add(dateparser.parse(r["d"]).date())
                except:
                    pass
    streak = 0
    curr = date.today()
    while curr in completed_dates:
        streak += 1
        curr = curr - timedelta(days=1)
    return streak

# -----------------------------
# Styling (light/dark)
# -----------------------------
def inject_css(dark_mode=False):
    if dark_mode:
        css = """
        <style>
        .stApp { background-color: #0f172a; color: #e6eef8; }
        .card { background:#0b1220; border-radius:10px; padding:12px; box-shadow: 0 6px 18px rgba(2,6,23,0.5); }
        .small { font-size:13px; color:#9fb0d4; }
        </style>
        """
    else:
        css = """
        <style>
        .stApp { background-color: #f8fafc; color: #0b1220; }
        .card { background:#ffffff; border-radius:10px; padding:12px; box-shadow: 0 6px 18px rgba(15,23,42,0.06); }
        .small { font-size:13px; color:#475569; }
        </style>
        """
    st.markdown(css, unsafe_allow_html=True)

# -----------------------------
# App UI
# -----------------------------
init_db()

if "dark" not in st.session_state:
    st.session_state.dark = False

st.sidebar.title("Settings")
st.sidebar.checkbox("Dark mode", value=st.session_state.dark, key="dark", on_change=lambda: st.session_state.__setitem__("dark", not st.session_state.dark))
inject_css(st.session_state.dark)

st.title("Lumos — Smooth To-Do & Productivity")
st.caption("Feature-rich, no API keys. Ready for your portfolio.")

# Top stats
all_tasks = fetch_tasks(filter_by="all", sort_by="created_desc")
progress = calc_progress(all_tasks)
st.subheader("Overview")
c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    st.metric("Progress", f"{progress} %")
    st.progress(progress)
with c2:
    total = len(all_tasks)
    st.metric("Total tasks", total)
with c3:
    streak = calc_streak()
    st.metric("Streak (days)", streak, delta="+ keep going" if streak > 0 else "")

st.markdown("---")

# Add task area
st.header("Add a Task")
with st.form("add_task", clear_on_submit=True):
    raw_text = st.text_input("Describe the task (natural language) — e.g., 'Submit report by Friday 5pm, high priority'")
    title_manual = st.text_input("Or provide a short title (optional)")
    desc_manual = st.text_area("Description (optional)", height=80)
    cat_choice = st.selectbox("Category (optional)", ["Auto", "Work", "Study", "Health", "Personal", "Other"])
    priority_choice = st.selectbox("Priority", [1, 2, 3, 4, 5], index=2, format_func=lambda x: {1:"1 (High)",2:"2",3:"3 (Medium)",4:"4",5:"5 (Low)"}[x])
    due_input = st.text_input("Due (optional - natural language)", placeholder="e.g. tomorrow 5pm or 2025-09-10 18:00")
    submit = st.form_submit_button("Add Task")

    if submit:
        # Determine title
        title = title_manual.strip() if title_manual.strip() else (raw_text.strip() if raw_text.strip() else None)
        if not title:
            st.warning("Please provide a task (title or description).")
        else:
            # Category
            if cat_choice == "Auto":
                category = auto_categorize(title + " " + (desc_manual or ""))
            else:
                category = cat_choice
            # due
            due_iso = parse_due_date(due_input) if due_input.strip() else None
            add_task(title, desc_manual.strip() or None, category, priority_choice, due_iso)
            st.success("Task added ✓")
            st.rerun()

st.markdown("---")

# Filters & sorting
st.subheader("Tasks")
colf1, colf2 = st.columns([2, 2])
with colf1:
    filter_by = st.selectbox("Filter", ["all", "pending", "done"])
with colf2:
    sort_by = st.selectbox("Sort by", ["created_desc", "due_asc", "priority_asc", "created_asc"], index=0, format_func=lambda x: {"created_desc":"Newest","due_asc":"Due date","priority_asc":"Priority","created_asc":"Oldest"}[x])

tasks = fetch_tasks(filter_by=filter_by, sort_by=sort_by)

if not tasks:
    st.info("No tasks match your filter. Add one above!")
else:
    for t in tasks:
        # Display each task as a "card"
        tid = t["id"]
        title = t["title"]
        desc = t.get("description") or ""
        category = t.get("category") or "Other"
        priority = t.get("priority") or 3
        due = t.get("due_date")
        completed = bool(t.get("completed"))
        created_at = t.get("created_at")
        completed_at = t.get("completed_at")

        overdue = is_overdue(due) and not completed

        # Row layout
        cols = st.columns([0.7, 3, 1, 1])
        with cols[0]:
            # checkbox for completion
            checked = st.checkbox("", value=completed, key=f"chk_{tid}")
            if checked != completed:
                if checked:
                    update_task(tid, completed=1, completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                else:
                    update_task(tid, completed=0, completed_at=None)
                st.rerun()

        with cols[1]:
            # Title + desc
            title_line = f"**{title}**  <span class='small'>— {category}</span>"
            if overdue:
                title_line += "  <span style='color:#ef4444;'>Overdue</span>"
            st.markdown(title_line, unsafe_allow_html=True)
            if desc:
                st.markdown(f"<div class='card small'>{desc}</div>", unsafe_allow_html=True)
            # meta
            meta = f"Due: {format_due(due)} • Created: {created_at or 'N/A'}"
            if completed and completed_at:
                meta += f" • Completed: {completed_at}"
            st.markdown(f"<div class='small'>{meta}</div>", unsafe_allow_html=True)

        with cols[2]:
            # priority badge + edit button
            st.markdown(priority_badge(priority), unsafe_allow_html=True)
            if st.button("Edit", key=f"edit_{tid}"):
                # Show a modal-like form inline (simple)
                with st.form(f"edit_form_{tid}"):
                    new_title = st.text_input("Title", value=title)
                    new_desc = st.text_area("Description", value=desc)
                    new_cat = st.selectbox("Category", ["Work", "Study", "Health", "Personal", "Other"], index=0 if category=="Work" else (1 if category=="Study" else (2 if category=="Health" else (3 if category=="Personal" else 4))))
                    new_pr = st.selectbox("Priority", [1,2,3,4,5], index=int(priority)-1, format_func=lambda x: {1:"1 (High)",2:"2",3:"3 (Medium)",4:"4",5:"5 (Low)"}[x])
                    new_due = st.text_input("Due (natural language)", value=format_due(due) if due else "")
                    save = st.form_submit_button("Save")
                    if save:
                        due_iso_new = parse_due_date(new_due) if new_due.strip() else None
                        update_task(tid, title=new_title, description=new_desc, category=new_cat, priority=new_pr, due_date=due_iso_new)
                        st.success("Updated")
                        st.rerun()
        with cols[3]:
            if st.button("Delete", key=f"del_{tid}"):
                delete_task(tid)
                st.success("Deleted")
                st.rerun()

st.markdown("---")
# Summary / Insights
st.header("Quick Insights")
ins1, ins2, ins3 = st.columns(3)
with ins1:
    st.metric("Completed", sum(1 for t in all_tasks if t.get("completed")))
with ins2:
    st.metric("Pending", sum(1 for t in all_tasks if not t.get("completed")))
with ins3:
    upcoming = sum(1 for t in all_tasks if (t.get("due_date") and not t.get("completed") and dateparser.parse(t["due_date"]).date() == date.today()))
    st.metric("Due today", upcoming)

st.markdown("**Tips:** Keep a short title, set at least tentative due dates, and try to complete one high-priority task daily!")
