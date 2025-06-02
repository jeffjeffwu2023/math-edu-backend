from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from bson import ObjectId
from .auth import get_current_user
import os
from dotenv import load_dotenv

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter(prefix="/api/assignments", tags=["assignments"])

class AssignmentCreate(BaseModel):
    questionIds: list[str]
    studentIds: list[str]

@router.post("/")
async def create_assignment(assignment: AssignmentCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "tutor"]:
        raise HTTPException(403, "Only admins or tutors can create assignments")
    
    # Validate question IDs
    valid_questions = await db.questions.find({"id": {"$in": assignment.questionIds}}).to_list(None)
    if len(valid_questions) != len(assignment.questionIds):
        raise HTTPException(400, "Some question IDs are invalid")
    
    # Fetch tutor's students if tutor
    if current_user["role"] == "tutor":
        tutor_students = await db.users.find(
            {"role": "student", "tutorId": current_user["id"]}
        ).to_list(None)
        tutor_student_ids = {student["id"] for student in tutor_students}
        # Verify all studentIds belong to the tutor
        invalid_student_ids = set(assignment.studentIds) - tutor_student_ids
        if invalid_student_ids:
            raise HTTPException(
                403, f"Students not assigned to this tutor: {invalid_student_ids}"
            )
    
    # Validate student IDs exist
    valid_students = await db.users.find(
        {"id": {"$in": assignment.studentIds}, "role": "student"}
    ).to_list(None)
    if len(valid_students) != len(assignment.studentIds):
        invalid_ids = set(assignment.studentIds) - {s["id"] for s in valid_students}
        raise HTTPException(404, f"Students not found: {invalid_ids}")
    
    # Create assignments for each student
    created_assignments = []
    for student_id in assignment.studentIds:
        assignment_dict = {
            "id": str(ObjectId()),
            "questionIds": assignment.questionIds,
            "studentId": student_id,
            "tutorId": current_user["id"],
            "submitted": False,
            "createdAt": datetime.utcnow()
        }
        await db.assignments.insert_one(assignment_dict)
        created_assignments.append(assignment_dict["id"])
    
    return {
        "message": "Assignments created successfully",
        "assignmentIds": created_assignments
    }

@router.get("/")
async def get_assignments(student_id: str = None, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "tutor"] and current_user["id"] != student_id:
        raise HTTPException(403, "Unauthorized access")
    query = {"studentId": student_id} if student_id else {}
    assignments = await db.assignments.find(query).to_list(None)
    return [
        {
            "id": assignment["id"],
            "questionIds": assignment.get("questionIds", []),  # Default to empty list
            "studentId": assignment["studentId"],
            "tutorId": assignment.get("tutorId", ""),
            "submitted": assignment["submitted"],
            "createdAt": assignment["createdAt"]
        }
        for assignment in assignments
    ]

@router.put("/submit/{assignment_id}")
async def submit_assignment(assignment_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student":
        raise HTTPException(403, "Only students can submit assignments")
    assignment = await db.assignments.find_one({"id": assignment_id})
    if not assignment or assignment["studentId"] != current_user["id"]:
        raise HTTPException(404, "Assignment not found or unauthorized")
    result = await db.assignments.update_one(
        {"id": assignment_id},
        {"$set": {"submitted": True}}
    )
    if result.modified_count == 0:
        raise HTTPException(400, "Failed to submit assignment")
    return {"message": "Assignment submitted"}