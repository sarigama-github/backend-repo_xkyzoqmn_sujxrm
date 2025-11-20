import os
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId
from datetime import datetime

from database import db, create_document, get_documents
from schemas import Marine, PirateCrew, PirateMember, Event

app = FastAPI(title="Grandline - One Piece Fanverse API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Utility
class IdResponse(BaseModel):
    id: str


def to_str_id(doc):
    if doc is None:
        return None
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d


@app.get("/")
async def root():
    return {"message": "Grandline API running"}


@app.get("/test")
async def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


# --- Admin auth ---
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "changeme")


def admin_required(authorization: Optional[str] = Header(None, alias="Authorization")):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization.split(" ", 1)[1].strip()
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")
    return True


# Marines
@app.post("/api/marines", response_model=IdResponse, dependencies=[Depends(admin_required)])
async def create_marine(marine: Marine):
    new_id = create_document("marine", marine)
    return {"id": new_id}

@app.get("/api/marines")
async def list_marines(limit: Optional[int] = None):
    docs = get_documents("marine", {}, limit)
    return [to_str_id(d) for d in docs]


# Pirate Crews
@app.post("/api/crews", response_model=IdResponse, dependencies=[Depends(admin_required)])
async def create_crew(crew: PirateCrew):
    new_id = create_document("piratecrew", crew)
    return {"id": new_id}

@app.get("/api/crews")
async def list_crews(sea: Optional[str] = None, crew_of_month: Optional[bool] = None):
    query = {}
    if sea:
        # exact match only, prevents operator injection
        query["sea"] = sea
    if crew_of_month is not None:
        query["crew_of_month"] = crew_of_month
    docs = get_documents("piratecrew", query)
    return [to_str_id(d) for d in docs]

@app.get("/api/crews/{crew_id}")
async def get_crew(crew_id: str):
    try:
        doc = db["piratecrew"].find_one({"_id": ObjectId(crew_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid crew id")
    if not doc:
        raise HTTPException(status_code=404, detail="Crew not found")
    crew = to_str_id(doc)
    members = list(db["piratemember"].find({"crew_id": crew["id"]}))
    crew["members"] = [to_str_id(m) for m in members]
    return crew


# Pirate Members
@app.post("/api/members", response_model=IdResponse, dependencies=[Depends(admin_required)])
async def create_member(member: PirateMember):
    # ensure crew exists
    try:
        crew = db["piratecrew"].find_one({"_id": ObjectId(member.crew_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid crew id")
    if not crew:
        raise HTTPException(status_code=404, detail="Crew not found")
    new_id = create_document("piratemember", member)
    return {"id": new_id}

@app.get("/api/members")
async def list_members(crew_id: Optional[str] = None):
    q = {"crew_id": crew_id} if crew_id else {}
    docs = get_documents("piratemember", q)
    return [to_str_id(d) for d in docs]


# Events
@app.post("/api/events", response_model=IdResponse, dependencies=[Depends(admin_required)])
async def create_event(event: Event):
    new_id = create_document("event", event)
    return {"id": new_id}

@app.get("/api/events")
async def list_events(status: Optional[str] = None):
    q = {"status": status} if status else {}
    docs = get_documents("event", q)
    return [to_str_id(d) for d in docs]

@app.get("/api/events/{event_id}")
async def get_event(event_id: str):
    try:
        doc = db["event"].find_one({"_id": ObjectId(event_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    if not doc:
        raise HTTPException(status_code=404, detail="Event not found")
    return to_str_id(doc)


# Leaderboard (top bounties)
@app.get("/api/leaderboard")
async def leaderboard(limit: int = 10):
    # limit is int from query parameters, FastAPI parses safely
    cursor = db["piratemember"].find({}).sort("bounty", -1).limit(limit)
    return [to_str_id(d) for d in cursor]


# --- Admin utilities ---
class SeedResponse(BaseModel):
    created: dict

@app.post("/api/admin/seed", response_model=SeedResponse, dependencies=[Depends(admin_required)])
async def seed_data(force: bool = False):
    created = {"marines": 0, "crews": 0, "members": 0, "events": 0}

    # Seed Marines
    if force or db["marine"].estimated_document_count() == 0:
        marines = [
            Marine(name="Sakazuki (Akainu)", rank="Fleet Admiral", bio="Absolute Justice proponent"),
            Marine(name="Borsalino (Kizaru)", rank="Admiral", bio="Light-speed tactician"),
        ]
        for m in marines:
            create_document("marine", m)
            created["marines"] += 1

    # Seed Crews and Members
    if force or db["piratecrew"].estimated_document_count() == 0:
        crews = [
            PirateCrew(name="Straw Hat Pirates", sea="Grand Line", description="Led by Monkey D. Luffy", crew_of_month=True),
            PirateCrew(name="Red-Haired Pirates", sea="Grand Line", description="Crew of Emperor Shanks"),
            PirateCrew(name="Arlong Pirates", sea="East Blue", description="Fish-man supremacists"),
        ]
        crew_ids = []
        for c in crews:
            cid = create_document("piratecrew", c)
            crew_ids.append((c.name, cid))
            created["crews"] += 1

        # map crew names to ids
        crew_map = {name: cid for name, cid in crew_ids}
        members = [
            PirateMember(crew_id=crew_map["Straw Hat Pirates"], name="Monkey D. Luffy", role="Captain", bounty=3000000000),
            PirateMember(crew_id=crew_map["Straw Hat Pirates"], name="Roronoa Zoro", role="Swordsman", bounty=1111000000),
            PirateMember(crew_id=crew_map["Straw Hat Pirates"], name="Nami", role="Navigator", bounty=366000000),
            PirateMember(crew_id=crew_map["Red-Haired Pirates"], name="Shanks", role="Captain", bounty=4048900000),
            PirateMember(crew_id=crew_map["Arlong Pirates"], name="Arlong", role="Captain", bounty=20000000),
        ]
        for m in members:
            create_document("piratemember", m)
            created["members"] += 1

    # Seed Events
    if force or db["event"].estimated_document_count() == 0:
        now = datetime.utcnow()
        events = [
            Event(title="Battle of Marineford Anniversary", description="Commemoration event with trivia and duels", date=now, status="upcoming"),
            Event(title="Grandline Cup", description="PvP tournament results posted", date=now, status="completed"),
        ]
        for e in events:
            create_document("event", e)
            created["events"] += 1

    return {"created": created}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
