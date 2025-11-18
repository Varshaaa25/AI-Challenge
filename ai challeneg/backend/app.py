from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import secrets
import string
import asyncio

app = FastAPI()

app.mount("/static", StaticFiles(directory="./static"), name="static")
templates = Jinja2Templates(directory="./static")

# In-memory sessions
# session_id -> {
#   'players': {ws_id: {'ws': WebSocket, 'name': str, 'secret': str or None, 'locked': bool}},
#   'turn': ws_id or None,
#   'history': [ {from: ws_id, guess: '1234', correct_digits: 2, correct_positions: 1} ]
# }
SESSIONS = {}

def make_session_code(n=6):
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(n))

def validate_secret(s):
    return len(s) == 4 and s.isdigit() and len(set(s)) == 4

def feedback(secret, guess):
    # counts
    correct_digits = sum(1 for d in guess if d in secret)
    correct_positions = sum(1 for a, b in zip(secret, guess) if a == b)
    return correct_digits, correct_positions

async def broadcast(session_id, message):
    session = SESSIONS.get(session_id)
    if not session: return
    for pid, p in session['players'].items():
        try:
            await p['ws'].send_json(message)
        except Exception:
            pass

@app.get('/')
async def index(request: Request):
    return templates.TemplateResponse('index.html', {"request": request})

@app.websocket('/ws/{session_id}/{player_id}')
async def ws_endpoint(websocket: WebSocket, session_id: str, player_id: str):
    await websocket.accept()
    # create session if not exists
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {'players': {}, 'turn': None, 'history': [], 'winner': None}

    session = SESSIONS[session_id]

    # Register player
    session['players'][player_id] = {'ws': websocket, 'name': player_id, 'secret': None, 'locked': False}

    # notify
    await broadcast(session_id, {'type': 'players', 'players': list(session['players'].keys())})

    try:
        while True:
            data = await websocket.receive_json()
            typ = data.get('type')

            if typ == 'set_secret':
                s = data.get('secret')
                if not validate_secret(s):
                    await websocket.send_json({'type': 'error', 'message': 'Invalid secret. Must be 4 unique digits.'})
                    continue
                session['players'][player_id]['secret'] = s
                session['players'][player_id]['locked'] = False
                await broadcast(session_id, {'type': 'player_update', 'player': player_id, 'locked': False})

            elif typ == 'lock_secret':
                if session['players'][player_id]['secret'] is None:
                    await websocket.send_json({'type': 'error', 'message': 'Set a valid secret before locking.'})
                    continue
                session['players'][player_id]['locked'] = True
                # If two players are locked, decide who starts
                await broadcast(session_id, {'type': 'player_update', 'player': player_id, 'locked': True})
                if len(session['players']) == 2 and all(p['locked'] for p in session['players'].values()):
                    # pick current turn if not set
                    if session['turn'] is None:
                        session['turn'] = next(iter(session['players'].keys()))
                    await broadcast(session_id, {'type': 'game_start', 'turn': session['turn']})

            elif typ == 'guess':
                guess = data.get('guess')
                # check turn
                if session['turn'] != player_id:
                    await websocket.send_json({'type': 'error', 'message': 'Not your turn.'})
                    continue
                if not validate_secret(guess):
                    await websocket.send_json({'type': 'error', 'message': 'Invalid guess.'})
                    continue
                # find opponent
                opponents = [pid for pid in session['players'].keys() if pid != player_id]
                if not opponents:
                    await websocket.send_json({'type': 'error', 'message': 'No opponent.'})
                    continue
                opp = session['players'][opponents[0]]
                if opp['secret'] is None:
                    await websocket.send_json({'type': 'error', 'message': 'Opponent has not set secret.'})
                    continue
                # if game already finished
                if session.get('winner'):
                    await websocket.send_json({'type': 'error', 'message': f'Game over. Winner: {session.get("winner")}'})
                    continue

                cd, cp = feedback(opp['secret'], guess)
                entry = {'from': player_id, 'guess': guess, 'correct_digits': cd, 'correct_positions': cp}
                session['history'].append(entry)

                # check win
                if cp == 4:
                    session['winner'] = player_id
                    session['turn'] = None
                    await broadcast(session_id, {'type': 'game_over', 'winner': player_id, 'entry': entry, 'history': session['history']})
                else:
                    # switch turn
                    session['turn'] = opponents[0]
                    await broadcast(session_id, {'type': 'guess_result', 'entry': entry, 'turn': session['turn'], 'history': session['history']})

            elif typ == 'leave':
                break

    except WebSocketDisconnect:
        pass
    finally:
        # cleanup
        if session_id in SESSIONS and player_id in SESSIONS[session_id]['players']:
            del SESSIONS[session_id]['players'][player_id]
            await broadcast(session_id, {'type': 'players', 'players': list(SESSIONS[session_id]['players'].keys())})
            # if session empty remove
            if not SESSIONS[session_id]['players']:
                del SESSIONS[session_id]

if __name__ == '__main__':
    uvicorn.run('app:app', host='0.0.0.0', port=8000, reload=True)
