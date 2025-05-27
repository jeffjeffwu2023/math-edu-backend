# routes/classrooms.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter(prefix="/api/classrooms", tags=["classrooms"])

class Address(BaseModel):
    street: str
    city: str
    state: str
    zip: str
    country: str

class ClassroomCreate(BaseModel):
    name: str
    address: Address
    managerIds: List[str]

class Classroom(ClassroomCreate):
    id: str
    createdAt: datetime

@router.post("/", response_model=Classroom)
async def create_classroom(classroom: ClassroomCreate):
    if await db.classrooms.find_one({"name": classroom.name}):
        raise HTTPException(400, "Classroom name already exists")
    
    # Verify managers exist
    for manager_id in classroom.managerIds:
        if not await db.users.find_one({"id": manager_id}):
            raise HTTPException(404, f"Manager with id {manager_id} not found")
    
    classroom_dict = classroom.dict()
    classroom_dict["id"] = str(ObjectId())
    classroom_dict["createdAt"] = datetime.utcnow()
    await db.classrooms.insert_one(classroom_dict)
    
    if classroom.managerIds:
        await db.users.update_many(
            {"id": {"$in": classroom.managerIds}},
            {"$addToSet": {"classroomIds": classroom_dict["id"]}}
        )
    
    return classroom_dict

@router.get("/", response_model=List[Classroom])
async def get_classrooms():
    classrooms = await db.classrooms.find().to_list(None)
    return [
        {**c, "id": c["id"]} for c in classrooms
    ]

@router.put("/{id}")
async def update_classroom(id: str, classroom: ClassroomCreate):
    # Verify managers exist
    for manager_id in classroom.managerIds:
        if not await db.users.find_one({"id": manager_id}):
            raise HTTPException(404, f"Manager with id {manager_id} not found")
    
    old_classroom = await db.classrooms.find_one({"id": id})
    if not old_classroom:
        raise HTTPException(404, "Classroom not found")
    
    old_manager_ids = set(old_classroom.get("managerIds", []))
    new_manager_ids = set(classroom.managerIds)
    
    await db.users.update_many(
        {"id": {"$in": list(old_manager_ids - new_manager_ids)}},
        {"$pull": {"classroomIds": id}}
    )
    await db.users.update_many(
        {"id": {"$in": classroom.managerIds}},
        {"$addToSet": {"classroomIds": id}}
    )
    
    result = await db.classrooms.update_one(
        {"id": id},
        {"$set": classroom.dict()}
    )
    if result.modified_count == 0:
        raise HTTPException(404, "Classroom not found")
    return {"message": "Classroom updated"}

@router.delete("/{id}")
async def delete_classroom(id: str):
    classroom = await db.classrooms.find_one({"id": id})
    if not classroom:
        raise HTTPException(404, "Classroom not found")
    await db.users.update_many(
        {"classroomIds": id},
        {"$pull": {"classroomIds": id}}
    )
    await db.classrooms.delete_one({"id": id})
    return {"message": "Classroom deleted"}