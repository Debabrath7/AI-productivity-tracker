import streamlit as st
import sqlite3
from sqlite3 import Connection
from datetime import datetime, date, timedelta
import pandas as pd

DB_PATH = "tasks.db"
st.set_page_config(page_title="AI-Productivity-Tracker", page_icon="🧠", layout="centered")

# ----------------- DB Setup -----------------
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
            title TEXT,
            description TEXT,
            category TEXT,
            priority INTEGER,
            due_date TEXT,
            completed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()

init_db()

# ----------------- Dark Theme CSS -----------------
st.markdown("""
<style>
/* Force dark mode */
.stApp {
    background-color:#0f172a !important;
    color:#e2e8f0 !important;
    font-family: 'Inter', sans-serif;
}
h1,h2,h3,h4,h5,h6,label,span,small,div {
    color:#e2e8f0 !important;
}
.card {
    background:#1e293b;
    border-radius:12px;
    padding:16px;
    margin-bottom:12px;
    box-shadow:0 4px 12px rgba(0,0,0,0.3);
}
.metric { text-align:center; font-size:22px; font-weight:600; }
.priority-high { color:#f87171; font-weight:600; }
.priority-med { color:#fb923c; font-weight:600; }
.priority-low { color:#4ade80; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ----------------- Helper Functions -----------------
def fetch_tasks_df():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM tasks ORDER BY created_at DESC", conn)
    conn.close()
    return df

def add_task(title, desc, priority, due):
    conn = get_conn()
    conn.execute("INSERT INTO tasks (title, description, priority, due_date) VALUES (?,?,?,?)",
                 (title, desc, priority, due if due else None))
    conn.commit()
    conn.close()

def toggle_task(task_id, completed):
    conn = get_conn()
    conn.execute("UPDATE tasks SET completed=?, completed_at=? WHERE id=?",
                 (completed, datetime.now().isoformat() if completed else None, task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = get_conn()
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def edit_task(task_id, new_title, new_desc, new_priority, new_due):
    conn = get_conn()
    conn.execute("UPDATE tasks SET title=?, description=?, priority=?, due_date=? WHERE id=?",
                 (new_title, new_desc, new_priority, new_due, task_id))
    conn.commit()
    conn.close()

def get_streak(df):
    if df.empty or "completed_at" not in df.columns:
        return 0
    df = df[df["completed"] == 1].dropna(subset=["completed_at"])
    if df.empty:
        return 0
    df["completed_at"] = pd.to_datetime(df["completed_at"]).dt.date
    today = date.today()
    streak = 0
    while today - timedelta(days=streak) in df["completed_at"].values:
        streak += 1
    return streak

# ----------------- Load Data -----------------
df = fetch_tasks_df()
done = df["completed"].sum() if not df.empty else 0
total = len(df)
progress = (done / total) * 100 if total > 0 else 0
streak = get_streak(df)

# ----------------- UI -----------------
st.title("✨ Lumos Productivity Tracker")
st.markdown("---")

# Overview
st.subheader("📊 Overview")
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f"<div class='card metric'>{progress:.0f}%<br>Progress</div>", unsafe_allow_html=True)
with c2: st.markdown(f"<div class='card metric'>{total}<br>Total</div>", unsafe_allow_html=True)
with c3: st.markdown(f"<div class='card metric'>{streak} 🔥<br>Streak</div>", unsafe_allow_html=True)

st.progress(progress/100 if total > 0 else 0)
st.markdown("---")

# Add Task
st.subheader("➕ Add Task")
with st.form("task_form"):
    colf1, colf2 = st.columns([3,1])
    with colf1:
        title = st.text_input("Task Title")
    with colf2:
        priority = st.selectbox("Priority", [1,2,3,4,5], index=2)
    desc = st.text_area("Description", height=80)
    due = st.text_input("Due (YYYY-MM-DD)")
    submitted = st.form_submit_button("Add Task")
    if submitted and title.strip():
        add_task(title, desc, priority, due)
        st.success("Task Added ✅")
        st.rerun()

st.markdown("---")

# Show Tasks
st.subheader("📂 Tasks")
filter_status = st.radio("Filter", ["All", "Pending", "Completed"], horizontal=True)
sort_by = st.selectbox("Sort by", ["Created Time", "Due Date", "Priority"])

rows = df.copy()
if filter_status == "Pending":
    rows = rows[rows["completed"] == 0]
elif filter_status == "Completed":
    rows = rows[rows["completed"] == 1]

if sort_by == "Due Date":
    rows = rows.sort_values(by="due_date", na_position="last")
elif sort_by == "Priority":
    rows = rows.sort_values(by="priority")

if rows.empty:
    st.info("No tasks match your filter.")
else:
    for _, r in rows.iterrows():
        priority_class = "priority-low" if r["priority"] >=4 else "priority-med" if r["priority"] == 3 else "priority-high"
        overdue = False
        if r["due_date"]:
            try:
                due_dt = datetime.fromisoformat(r["due_date"]).date()
                if due_dt < date.today() and not r["completed"]:
                    overdue = True
            except:
                pass
        with st.container():
            col1, col2 = st.columns([8,2])
            with col1:
                st.markdown(
                    f"""
                    <div class='card'>
                    <b>{'✅' if r['completed'] else '⬜'} {r['title']}</b> 
                    <span class='{priority_class}'>[P{r['priority']}]</span><br>
                    <small>{r['description'] or ''}</small><br>
                    <i>Due: {r['due_date'] or 'None'}</i> {"⚠️ Overdue" if overdue else ""}
                    </div>
                    """, unsafe_allow_html=True
                )
            with col2:
                if not r["completed"]:
                    if st.button("Mark Done", key=f"done{r['id']}"):
                        toggle_task(r["id"], 1)
                        st.rerun()
                else:
                    if st.button("Undo", key=f"undo{r['id']}"):
                        toggle_task(r["id"], 0)
                        st.rerun()
                if st.button("✏️ Edit", key=f"edit{r['id']}"):
                    with st.form(f"edit_form{r['id']}"):
                        new_title = st.text_input("Edit Title", r["title"])
                        new_desc = st.text_area("Edit Description", r["description"])
                        new_priority = st.selectbox("Edit Priority", [1,2,3,4,5], index=r["priority"]-1)
                        new_due = st.text_input("Edit Due", r["due_date"] or "")
                        save = st.form_submit_button("Save")
                        if save:
                            edit_task(r["id"], new_title, new_desc, new_priority, new_due)
                            st.rerun()
                if st.button("🗑️ Delete", key=f"del{r['id']}"):
                    delete_task(r["id"])
                    st.rerun()
