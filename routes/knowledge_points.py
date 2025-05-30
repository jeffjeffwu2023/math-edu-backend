# routes/knowledge_points.py
from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
from dotenv import load_dotenv
from typing import Optional, List
from datetime import datetime
from models.knowledge_point import KnowledgePoint, KnowledgePointResponse

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter(prefix="/api/knowledge-points", tags=["knowledge_points"])

@router.get("/", response_model=List[KnowledgePointResponse])
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
    points = await db.knowledge_points.find(query).to_list(None)
    if not points:
        raise HTTPException(404, "No knowledge points found")
    return [
        {
            "id": str(p["id"]),
            "grade": p["grade"],
            "strand": p["strand"],
            "topic": p["topic"],
            "skill": p["skill"],
            "subKnowledgePoint": p["subKnowledgePoint"],
            "version": p["version"],
            "isActive": p["isActive"],
            "createdAt": p["createdAt"],
            "updatedAt": p["updatedAt"]
        }
        for p in points
    ]

@router.post("/", response_model=KnowledgePointResponse)
async def add_knowledge_point(kp: KnowledgePoint):
    kp_dict = kp.dict(exclude={"id"})
    kp_dict["createdAt"] = datetime.utcnow().isoformat()
    kp_dict["updatedAt"] = datetime.utcnow().isoformat()
    kp_dict["isActive"] = True
    result = await db.knowledge_points.insert_one(kp_dict)
    kp_dict["id"] = str(result.inserted_id)
    return kp_dict

@router.put("/{id}", response_model=KnowledgePointResponse)
async def update_knowledge_point(id: str, kp: KnowledgePoint):
    try:
        kp_id = ObjectId(id)
    except:
        raise HTTPException(400, "Invalid knowledge point ID")
    
    existing = await db.knowledge_points.find_one({"_id": kp_id, "isActive": True})
    if not existing:
        raise HTTPException(404, "Knowledge point not found")
    
    kp_dict = kp.dict(exclude={"id"})
    kp_dict["updatedAt"] = datetime.utcnow().isoformat()
    kp_dict["isActive"] = True
    await db.knowledge_points.update_one({"_id": kp_id}, {"$set": kp_dict})
    kp_dict["id"] = id
    return kp_dict

@router.delete("/{id}")
async def delete_knowledge_point(id: str):
    try:
        kp_id = ObjectId(id)
    except:
        raise HTTPException(400, "Invalid knowledge point ID")
    
    result = await db.knowledge_points.update_one(
        {"_id": kp_id, "isActive": True},
        {"$set": {"isActive": False, "updatedAt": datetime.utcnow().isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(404, "Knowledge point not found or already deleted")
    return {"message": "Knowledge point deleted successfully"}