from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState
from threading import Timer
import uvicorn
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get():
    return HTMLResponse(open("static/index.html", encoding="utf-8").read())

clients = {"A": None, "B": None}
players = {"P": [], "C": [], "IF": [], "OF": []}
draft_started = False
turn = "A"
drafted = {"A": [], "B": []}
countdown = 0
countdown_timer = None

async def broadcast_state():
    state = {
        "type": "state",
        "teams": drafted,
        "available": players,
        "turn": turn if draft_started else None,
        "countdown": countdown if draft_started else None
    }
    for client in clients.values():
        if client and client.application_state == WebSocketState.CONNECTED:
            await client.send_text(json.dumps(state))

def start_countdown():
    global countdown, countdown_timer
    countdown = 20

    def tick():
        global countdown, countdown_timer
        countdown -= 1
        if countdown <= 0:
            countdown = 0
            countdown_timer = None
        else:
            countdown_timer = Timer(1.0, tick)
            countdown_timer.start()

    countdown_timer = Timer(1.0, tick)
    countdown_timer.start()

@app.websocket("/ws/{team}")
async def websocket_endpoint(websocket: WebSocket, team: str):
    await websocket.accept()
    clients[team] = websocket
    await broadcast_state()

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message["type"] == "add_players" and team == "A":
                for pos in ["P", "C", "IF", "OF"]:
                    players[pos] = message["players"].get(pos, [])
                await broadcast_state()

            elif message["type"] == "start_draft" and team == "A":
                global draft_started, turn, countdown_timer
                draft_started = True
                turn = "A"
                start_countdown()
                await broadcast_state()

            elif message["type"] == "pick" and draft_started and team == turn:
                pos = message["position"]
                player = message["player"]
                if player in players.get(pos, []):
                    players[pos].remove(player)
                    drafted[team].append(player)
                    if countdown_timer:
                        countdown_timer.cancel()
                    turn = "B" if turn == "A" else "A"
                    start_countdown()
                    await broadcast_state()

            elif message["type"] == "reset":
                global draft_started, turn, countdown_timer
                players["P"] = []
                players["C"] = []
                players["IF"] = []
                players["OF"] = []
                drafted["A"] = []
                drafted["B"] = []
                draft_started = False
                turn = "A"
                if countdown_timer:
                    countdown_timer.cancel()
                await broadcast_state()

    except WebSocketDisconnect:
        clients[team] = None
