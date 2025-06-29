import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketState

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

html = """
<!DOCTYPE html>
<html>
    <head>
        <meta http-equiv="refresh" content="0; url=/static/index.html" />
    </head>
    <body>
        <p>Redirecting to <a href="/static/index.html">index.html</a></p>
    </body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(html)

clients = {"A": None, "B": None}

state = {
    "available": {},
    "teams": {"A": [], "B": []},
    "turn": "A",
    "started": False,
    "finished": False,
    "countdown": 20
}

def broadcast_state_sync():
    data = json.dumps({"type": "state", **state})
    for team, client in clients.items():
        if client and client.application_state == WebSocketState.CONNECTED:
            asyncio.create_task(client.send_text(data))

async def countdown_timer():
    while state["started"] and not state["finished"]:
        await asyncio.sleep(1)
        state["countdown"] -= 1
        if state["countdown"] <= 0:
            state["turn"] = "B" if state["turn"] == "A" else "A"
            state["countdown"] = 20
        broadcast_state_sync()

@app.websocket("/ws/{team}")
async def websocket_endpoint(websocket: WebSocket, team: str):
    await websocket.accept()
    clients[team] = websocket
    broadcast_state_sync()

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg["type"] == "add_players":
                state["available"] = msg["players"]
                state["teams"] = {"A": [], "B": []}
                state["turn"] = "A"
                state["started"] = False
                state["finished"] = False
                state["countdown"] = 20

            elif msg["type"] == "start_draft":
                state["started"] = True
                state["finished"] = False
                asyncio.create_task(countdown_timer())

            elif msg["type"] == "reset":
                state["available"] = {}
                state["teams"] = {"A": [], "B": []}
                state["turn"] = "A"
                state["started"] = False
                state["finished"] = False
                state["countdown"] = 20

            elif msg["type"] == "pick":
                pos = msg["position"]
                player = msg["player"]
                if player in state["available"].get(pos, []):
                    state["teams"][team].append(player)
                    state["available"][pos].remove(player)

                    if all(len(players) == 0 for players in state["available"].values()):
                        state["finished"] = True
                    else:
                        state["turn"] = "B" if team == "A" else "A"
                        state["countdown"] = 20

            broadcast_state_sync()

    except WebSocketDisconnect:
        clients[team] = None
