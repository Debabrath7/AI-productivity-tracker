import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# ---------------------------
# Page Config
# ---------------------------
st.set_page_config(page_title="AI Productivity Tracker", page_icon="✅", layout="centered")

# Force dark mode look
st.markdown(
    """
    <style>
    body {
        background-color: #0e1117;
        color: #fafafa;
    }
    .stTextInput > div > div > input {
        background-color: #262730;
        color: white;
    }
    .stSelectbox div[data-baseweb="select"] > div {
        background-color: #262730;
        color: white;
    }
    .stDateInput > div > input {
        background-color: #262730;
        color: white;
    }
    .stButton > button {
        background-color: #262730;
        color: white;
        border-radius: 8px;
    }
    .task-card {
        padding: 15px;
        margin: 8px 0;
        border-radius: 8px;
        background-color: #1e1e2f;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# Database Setup
# ---------------------------
conn = sqlite3.connect("tasks.db", check_same_thread=False)
c = conn.cursor()

c.execute(
    """CREATE TABLE IF NOT EXISTS tasks
         (id INTEGER PRIMARY KEY AUTOINCREMENT,
          task TEXT,
          category TEXT,
          priority TEXT,
          due_date TEXT,
          status TEXT)"""
)
conn.commit()

# ---------------------------
# Helper Functions
# ---------------------------
def add_task(task, category, priority, due_date):
    c.execute("INSERT INTO tasks (task, category, priority, due_date, status) VALUES (?, ?, ?, ?, ?)",
              (task, category, priority, due_date, "Pending"))
    conn.commit()

def update_status(task_id, status):
    c.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))
    conn.commit()

def delete_task(task_id):
    c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()

def get_tasks():
    return pd.read_sql("SELECT * FROM tasks ORDER BY due_date", conn)

# ---------------------------
# App Layout
# ---------------------------
st.title("✅ AI Productivity Tracker")

# --- Add Task ---
st.subheader("➕ Add a New Task")
with st.form("task_form", clear_on_submit=True):
    task = st.text_input("Task Name")
    category = st.selectbox("Category", ["Work", "Study", "Personal", "Other"])
    priority = st.radio("Priority", ["High", "Medium", "Low"], horizontal=True)
    due_date = st.date_input("Due Date", datetime.now())
    submitted = st.form_submit_button("Add Task")

    if submitted and task.strip():
        add_task(task, category, priority, due_date.strftime("%Y-%m-%d"))
        st.success(f"Task '{task}' added successfully! ✅")

# --- Task List ---
st.subheader("📋 Your Tasks")
tasks_df = get_tasks()

if not tasks_df.empty:
    for _, row in tasks_df.iterrows():
        with st.container():
            st.markdown(
                f"""
                <div class="task-card">
                <b>{row['task']}</b><br>
                <small>
                Category: {row['category']} | Priority: {row['priority']} | Due: {row['due_date']} | Status: {row['status']}
                </small>
                </div>
                """,
                unsafe_allow_html=True
            )

            cols = st.columns([1, 1, 1])
            with cols[0]:
                if st.button("✅ Done", key=f"done_{row['id']}"):
                    update_status(row["id"], "Completed")
                    st.rerun()
            with cols[1]:
                if st.button("⌛ Pending", key=f"pending_{row['id']}"):
                    update_status(row["id"], "Pending")
                    st.rerun()
            with cols[2]:
                if st.button("❌ Delete", key=f"delete_{row['id']}"):
                    delete_task(row["id"])
                    st.rerun()
else:
    st.info("No tasks yet. Add one above! 🚀")
