import streamlit as st
import sqlite3
from sqlite3 import Connection
from datetime import datetime, date, timedelta
import dateparser
import os

DB_PATH = "tasks.db"
st.set_page_config(page_title="Lumos Productivity", page_icon="🧠", layout="centered")

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

# ----------------- Theme + Styling -----------------
if "dark" not in st.session_state:
    st.session_state.dark = False

def inject_css():
    css_light = """
    <style>
    .stApp { background-color:#f8fafc; color:#0f172a; font-family: 'Inter', sans-serif; }
    h1,h2,h3,h4,h5 { color:#0f172a; font-weight:600; }
    .card { background:#fff; border-radius:12px; padding:16px; margin-bottom:12px; box-shadow:0 4px 12px rgba(0,0,0,0.05); }
    .metric { text-align:center; font-size:22px; font-weight:600; }
    </style>
    """

    css_dark = """
    <style>
    .stApp { background-color:#0f172a; color:#e2e8f0; font-family: 'Inter', sans-serif; }
    h1,h2,h3,h4,h5 { color:#e2e8f0; font-weight:600; }
    .card { background:#1e293b; border-radius:12px; padding:16px; margin-bottom:12px; box-shadow:0 4px 12px rgba(0,0,0,0.3); }
    .metric { text-align:center; font-size:22px; font-weight:600; }
    </style>
    """

    st.markdown(css_dark if st.session_state.dark else css_light, unsafe_allow_html=True)

inject_css()

# ----------------- Header -----------------
col1, col2 = st.columns([8,1])
with col1:
    st.title("✨ Lumos Productivity Tracker")
with col2:
    st.button("🌙" if not st.session_state.dark else "☀️", 
              on_click=lambda: st.session_state.update({"dark": not st.session_state.dark}))

st.markdown("---")

# ----------------- Example Overview -----------------
st.subheader("📊 Overview")
c1, c2, c3 = st.columns(3)
with c1: st.markdown("<div class='card metric'>0%<br>Progress</div>", unsafe_allow_html=True)
with c2: st.markdown("<div class='card metric'>0<br>Total</div>", unsafe_allow_html=True)
with c3: st.markdown("<div class='card metric'>0<br>Streak</div>", unsafe_allow_html=True)

st.markdown("---")

# ----------------- Add Task -----------------
st.subheader("➕ Add Task")
with st.form("task_form"):
    colf1, colf2 = st.columns([3,1])
    with colf1:
        title = st.text_input("Task Title")
    with colf2:
        priority = st.selectbox("Priority", [1,2,3,4,5], index=2)
    desc = st.text_area("Description", height=80)
    due = st.text_input("Due (e.g. tomorrow 5pm)")
    submitted = st.form_submit_button("Add Task")
    if submitted and title.strip():
        conn = get_conn()
        conn.execute("INSERT INTO tasks (title, description, priority, due_date) VALUES (?,?,?,?)",
                     (title, desc, priority, due if due else None))
        conn.commit()
        conn.close()
        st.success("Task Added ✅")
        st.rerun()

st.markdown("---")

# ----------------- Show Tasks -----------------
st.subheader("📂 Tasks")
conn = get_conn()
rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
conn.close()

if not rows:
    st.info("No tasks yet — add one above!")
else:
    for r in rows:
        with st.container():
            st.markdown(
                f"""
                <div class='card'>
                <b>{r['title']}</b> — Priority {r['priority']}<br>
                <small>{r['description'] or ''}</small><br>
                <i>Due: {r['due_date'] or 'None'}</i>
                </div>
                """, unsafe_allow_html=True
            )
