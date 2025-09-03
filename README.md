# Lumos AI To-Do

AI-powered To-Do app designed for easy deployment on Render.  
Built with **Streamlit + SQLite** and optional **OpenAI** integration for NLP & task suggestions.

---

## Setup (local)

1. Create virtual env, install requirements:

bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

## Deploy to Render

Push this repo to GitHub.

On Render, create New Web Service → connect the repo.

## Build Command:

pip install -r requirements.txt


## Start Command:

streamlit run app.py --server.port $PORT --server.address 0.0.0.0


(Optional) Add environment variable:

OPENAI_API_KEY — enables AI features.
