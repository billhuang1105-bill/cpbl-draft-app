# app.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")

html_path = "static/index.html"

clients = {"A": None, "B": None}
available_players = {"P": [], "C": [], "IF": [], "OF": []}
teams = {"A": [], "B": []}
turn = "A"
started = False
finished = False

@app.get("/")
async def get():
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.websocket("/ws/{team}")
async def websocket_endpoint(websocket: WebSocket, team: str):
    global started, finished
    await websocket.accept()
    clients[team] = websocket
    await send_state()

    try:
        while True:
            data = await websocket.receive_json()
            if data["type"] == "add_players":
                for pos in available_players:
                    available_players[pos] = data["players"].get(pos, [])
                await send_state()
            elif data["type"] == "start_draft":
                started = True
                finished = False
                await send_state()
            elif data["type"] == "pick":
                pos, player = data["position"], data["player"]
                if player in available_players[pos]:
                    teams[team].append(player)
                    available_players[pos].remove(player)
                    turn = "B" if team == "A" else "A"
                    all_empty = all(len(v) == 0 for v in available_players.values())
                    if all_empty:
                        finished = True
                    await send_state()
            elif data["type"] == "reset":
                for pos in available_players:
                    available_players[pos] = []
                teams["A"] = []
                teams["B"] = []
                started = False
                finished = False
                turn = "A"
                await send_state()
    except WebSocketDisconnect:
        clients[team] = None

async def send_state():
    msg = {
        "type": "state",
        "available": available_players,
        "teams": teams,
        "turn": turn,
        "started": started,
        "finished": finished
    }
    for ws in clients.values():
        if ws:
            await ws.send_json(msg)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=10000, reload=True)
