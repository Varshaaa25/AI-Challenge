# Codebreaker Duel — FastAPI + React (single-file)

Quick hackathon implementation of the realtime 2-player Codebreaker Duel.

Prerequisites
- Python 3.10+
- pip

Install

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```


Run

Preferred (one-command helper):

```bash
cd "/Users/varsha.gajendra/Documents/ai challeneg/backend"
./run.sh
```

If you prefer not to use the helper script, start using the venv's python to run uvicorn (avoids `zsh: command not found: uvicorn`):

```bash
cd "/Users/varsha.gajendra/Documents/ai challeneg/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Open two browser windows to http://localhost:8000. Create a session code in one, copy it to the other and join.

How it works (short)
- WebSocket endpoint: /ws/{session_id}/{player_id}
- In-memory session store (SESSIONS dict) holds players, turn, history.
- Players set & lock secrets; when both locked the game starts and turns alternate.

Notes / next steps
- Persistence (Redis) and multi-process WebSocket support for scale.
- Improve UI, validation and UX polish.
