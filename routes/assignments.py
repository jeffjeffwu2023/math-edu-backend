# routes/assignments.py
from fastapi import APIRouter, HTTPException
from models.assignment import Assignment
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter()

@router.get("/")
async def get_assignments(student_id: str = None):
    try:
        query = {"studentId": student_id} if student_id else {}
        assignments = []
        async for assignment in db.assignments.find(query):
            assignment.pop("_id", None)  # Remove MongoDB's _id field
            assignments.append(assignment)
        return assignments
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def assign_homework(assignment: Assignment):
    try:
        assignment_dict = assignment.dict()
        existing_assignments = []
        async for assignment in db.assignments.find({}, {"_id": 0}):
            existing_assignments.append(assignment)
        assignment_dict["id"] = max([a["id"] for a in existing_assignments], default=0) + 1
        result = await db.assignments.insert_one(assignment_dict)
        return {"message": "Assignment created", "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/submit/{id}")
async def submit_assignment(id: int):
    try:
        result = await db.assignments.update_one({"id": id}, {"$set": {"submitted": True}})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Assignment not found")
        return {"message": "Assignment submitted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))