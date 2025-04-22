
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from db import SessionLocal, Match
from uuid import uuid4
from datetime import datetime
import os, json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StartMatchRequest(BaseModel):
    players: list[str]

class PointRequest(BaseModel):
    match_id: str
    player: int

class UndoRequest(BaseModel):
    match_id: str

@app.post("/match/start")
def start_match(req: StartMatchRequest):
    db = SessionLocal()
    match_id = str(uuid4())
    match = Match(
        id=match_id,
        players=req.players,
        sets=[[0, 0]],
        game_score=[0, 0],
        history=[],
        start_time=datetime.utcnow()
    )
    db.add(match)
    db.commit()
    db.close()
    return {"match_id": match_id}

@app.post("/match/point")
def add_point(req: PointRequest):
    db = SessionLocal()
    match = db.query(Match).filter(Match.id == req.match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Матч не найден")

    player = req.player
    opponent = 1 - player
    score = match.game_score or [0, 0]

    score[player] += 1

    if score[player] == 4 and score[opponent] < 3:
        update_game(match, player)
        score = [0, 0]
    elif score[player] == 4 and score[opponent] == 4:
        score = [3, 3]
    elif score[player] == 5:
        update_game(match, player)
        score = [0, 0]

    match.game_score = score
    match.history.append({
        "point": player,
        "time": datetime.utcnow().isoformat()
    })
    db.commit()
    db.close()
    return {"status": "ok"}

@app.post("/match/undo")
def undo_point(req: UndoRequest):
    db = SessionLocal()
    match = db.query(Match).filter(Match.id == req.match_id).first()
    if not match or not match.history:
        raise HTTPException(status_code=404, detail="Нет истории или матча")

    last = match.history.pop()
    match.game_score[last["point"]] = max(0, match.game_score[last["point"]] - 1)
    db.commit()
    db.close()
    return {"status": "undone"}

@app.get("/match/{match_id}")
def get_match(match_id: str):
    db = SessionLocal()
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Матч не найден")
    return {
        "players": match.players,
        "sets": match.sets,
        "game_score": match.game_score,
        "history": match.history,
        "status": match.status,
        "start_time": match.start_time.isoformat(),
        "end_time": match.end_time.isoformat() if match.end_time else None
    }

@app.get("/match/{match_id}/export")
def export_match(match_id: str):
    db = SessionLocal()
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Матч не найден")

    return {
        "match_id": match.id,
        "players": match.players,
        "score": {"sets": match.sets},
        "current_game_score": f"{match.game_score[0]}-{match.game_score[1]}",
        "events": match.history,
        "start_time": match.start_time.isoformat(),
        "end_time": match.end_time.isoformat() if match.end_time else None,
        "status": match.status
    }

@app.post("/match/end")
def end_match(req: UndoRequest):
    db = SessionLocal()
    match = db.query(Match).filter(Match.id == req.match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Матч не найден")

    match.status = "completed"
    match.end_time = datetime.utcnow()
    db.commit()

    export_path = "exports"
    os.makedirs(export_path, exist_ok=True)
    json_path = os.path.join(export_path, f"match_{match.id}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "match_id": match.id,
            "players": match.players,
            "score": {"sets": match.sets},
            "current_game_score": f"{match.game_score[0]}-{match.game_score[1]}",
            "events": match.history,
            "start_time": match.start_time.isoformat(),
            "end_time": match.end_time.isoformat(),
            "status": "completed"
        }, f, ensure_ascii=False, indent=2)

    db.close()
    return {"status": "completed", "exported_to": json_path}

def update_game(match, winner):
    sets = match.sets
    current_set = sets[-1]
    current_set[winner] += 1

    if current_set[winner] >= 6 and (current_set[winner] - current_set[1 - winner]) >= 2:
        if len(sets) == 1 or all(s[0] < 6 and s[1] < 6 for s in sets[:-1]):
            sets.append([0, 0])
