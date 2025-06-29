import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 靜態檔案提供（對應 index.html）
app.mount("/static", StaticFiles(directory="static"), name="static")

origins = ["*"]  # 為了讓不同裝置能連線
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全域狀態資料
players = {"P": [], "C": [], "IF": [], "OF": []}
teams = {"A": [], "B": []}
turn_order = ["A", "B"]
current_turn = None
countdown = 0
connected = {}

# 傳送目前狀態給所有用戶
async def broadcast_state():
    global countdown
    data = {
        "type": "state",
        "teams": teams,
        "available": players,
        "turn": current_turn,
        "countdown": countdown
    }
    for ws in connected.values():
        await ws.send_json(data)

# 倒數邏輯
async def start_countdown():
    global countdown
    countdown = 20
    while countdown > 0:
        await broadcast_state()
        await asyncio.sleep(1)
        countdown -= 1
    await broadcast_state()

@app.websocket("/ws/{team}")
async def websocket_endpoint(websocket: WebSocket, team: str):
    await websocket.accept()
    connected[team] = websocket
    await broadcast_state()

    try:
        while True:
            data = await websocket.receive_json()
            if data["type"] == "add_players" and team == "A":
                for pos in ["P", "C", "IF", "OF"]:
                    players[pos] = data["players"].get(pos, [])
                await broadcast_state()

            elif data["type"] == "start_draft" and team == "A":
                global current_turn
                current_turn = "A"
                await broadcast_state()
                asyncio.create_task(start_countdown())

            elif data["type"] == "pick":
                if team != current_turn:
                    continue
                pos = data["position"]
                name = data["player"]
                if name in players.get(pos, []):
                    players[pos].remove(name)
                    teams[team].append(name)
                    current_turn = "B" if team == "A" else "A"
                    await broadcast_state()
                    asyncio.create_task(start_countdown())

            elif data["type"] == "reset":
                players.update({k: [] for k in players})
                teams.update({"A": [], "B": []})
                current_turn = None
                countdown = 0
                await broadcast_state()

    except WebSocketDisconnect:
        del connected[team]
