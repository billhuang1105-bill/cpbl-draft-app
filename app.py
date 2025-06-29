# app.py
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
from collections import defaultdict
import json

app = FastAPI()

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, team: str):
        await websocket.accept()
        self.active_connections[team] = websocket

    def disconnect(self, team: str):
        if team in self.active_connections:
            del self.active_connections[team]

    async def send_to_team(self, team: str, message: dict):
        if team in self.active_connections:
            await self.active_connections[team].send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)

manager = ConnectionManager()

teams = {"A": [], "B": []}
available = {"P": [], "C": [], "IF": [], "OF": []}
turn = "A"
finished = False
started = False  # 標記是否已經開始選秀

def is_all_empty():
    return all(len(players) == 0 for players in available.values())

@app.websocket("/ws/{team}")
async def websocket_endpoint(websocket: WebSocket, team: str):
    global turn, finished, started
    await manager.connect(websocket, team)
    try:
        await manager.broadcast({"type": "state", "teams": teams, "available": available, "turn": turn, "finished": finished, "started": started})
        while True:
            data = await websocket.receive_json()
            if data["type"] == "add_players":
                for pos in data["players"]:
                    for p in data["players"][pos]:
                        if p not in available[pos]:
                            available[pos].append(p)
                started = False
                await manager.broadcast({"type": "state", "teams": teams, "available": available, "turn": turn, "finished": finished, "started": started})

            elif data["type"] == "start_draft":
                started = True
                await manager.broadcast({"type": "state", "teams": teams, "available": available, "turn": turn, "finished": finished, "started": started})

            elif data["type"] == "pick":
                if not started or turn != team:
                    continue
                pos = data["position"]
                player = data["player"]
                if player in available[pos]:
                    teams[team].append(player)
                    available[pos].remove(player)
                    turn = "B" if turn == "A" else "A"
                    finished = is_all_empty()
                await manager.broadcast({"type": "state", "teams": teams, "available": available, "turn": turn, "finished": finished, "started": started})

            elif data["type"] == "reset":
                teams["A"].clear()
                teams["B"].clear()
                available.clear()
                available.update({"P": [], "C": [], "IF": [], "OF": []})
                turn = "A"
                finished = False
                started = False
                await manager.broadcast({"type": "state", "teams": teams, "available": available, "turn": turn, "finished": finished, "started": started})

    except WebSocketDisconnect:
        manager.disconnect(team)

@app.get("/")
async def get():
    return HTMLResponse(open("static/index.html", encoding="utf-8").read())

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
