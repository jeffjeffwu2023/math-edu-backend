# routes/knowledge_points.py
from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter(prefix="/api/knowledge-points", tags=["knowledge_points"])

@router.get("/")
async def get_knowledge_points(
    grade: Optional[str] = None,
    strand: Optional[str] = None,
    topic: Optional[str] = None,
    skill: Optional[str] = None,
    version: Optional[str] = "2025.01"
):
    query = {"version": version, "isActive": True}
    if grade:
        query["grade"] = grade
    if strand:
        query["strand"] = strand
    if topic:
        query["topic"] = topic
    if skill:
        query["skill"] = skill
    points = await db.knowledge_points.find(query, {
        "_id": 1, "grade": 1, "strand": 1, "topic": 1, "skill": 1, "subKnowledgePoint": 1
    }).to_list(None)
    if not points:
        raise HTTPException(404, "No knowledge points found")
    return [{"_id": str(p["_id"]), "grade": p["grade"], "strand": p["strand"], "topic": p["topic"], "skill": p["skill"], "subKnowledgePoint": p["subKnowledgePoint"]} for p in points]