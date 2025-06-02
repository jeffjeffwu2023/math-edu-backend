# routes/courses.py
from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from typing import List
from datetime import datetime
from models.course import Course, CourseResponse
from .auth import get_current_user
import uuid

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter(prefix="/api/courses", tags=["courses"])

@router.post("/", response_model=CourseResponse)
async def create_course(course: Course, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(403, "Only admins can create courses")
    
    # Validate knowledge point and question IDs
    if course.knowledgePointIds:
        valid_kps = await db.knowledge_points.find(
            {"id": {"$in": course.knowledgePointIds}, "isActive": True}
        ).to_list(None)
        if len(valid_kps) != len(course.knowledgePointIds):
            raise HTTPException(400, "Some knowledge point IDs are invalid or inactive")
    
    if course.questionIds:
        valid_questions = await db.questions.find(
            {"id": {"$in": course.questionIds}, "isActive": True}
        ).to_list(None)
        if len(valid_questions) != len(course.questionIds):
            raise HTTPException(400, "Some question IDs are invalid or inactive")
    
    if await db.courses.find_one({"name": course.name, "grade": course.grade}):
        raise HTTPException(400, "Course with this name and grade already exists")
    
    course_dict = course.dict(exclude={"id"})
    course_dict["id"] = str(uuid.uuid4())
    course_dict["createdAt"] = datetime.utcnow().isoformat()
    course_dict["updatedAt"] = datetime.utcnow().isoformat()
    course_dict["isActive"] = True
    
    await db.courses.insert_one(course_dict)
    
    # Populate knowledge points and questions in response
    course_dict["knowledgePointIds"] = [
        {
            "id": kp["id"],
            "grade": kp["grade"],
            "strand": kp["strand"],
            "topic": kp["topic"],
            "skill": kp["skill"],
            "subKnowledgePoint": kp["subKnowledgePoint"]
        } for kp in valid_kps
    ] if course.knowledgePointIds else []
    course_dict["questionIds"] = [
        {
            "id": q["id"],
            "title": q["title"],
            "content": q["content"]
        } for q in valid_questions
    ] if course.questionIds else []
    
    return course_dict

@router.get("/", response_model=List[CourseResponse])
async def get_courses(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(403, "Only admins can access courses")
    
    courses = await db.courses.find({"isActive": True}).to_list(None)
    for course in courses:
        course["knowledgePointIds"] = await db.knowledge_points.find(
            {"id": {"$in": course["knowledgePointIds"]}, "isActive": True}
        ).to_list(None)
        course["knowledgePointIds"] = [
            {
                "id": kp["id"],
                "grade": kp["grade"],
                "strand": kp["strand"],
                "topic": kp["topic"],
                "skill": kp["skill"],
                "subKnowledgePoint": kp["subKnowledgePoint"]
            } for kp in course["knowledgePointIds"]
        ]
        course["questionIds"] = await db.questions.find(
            {"id": {"$in": course["questionIds"]}, "isActive": True}
        ).to_list(None)
        course["questionIds"] = [
            {
                "id": q["id"],
                "title": q["title"],
                "content": q["content"]
            } for q in course["questionIds"]
        ]
    return courses

@router.put("/{id}", response_model=CourseResponse)
async def update_course(id: str, course: Course, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(403, "Only admins can update courses")
    
    existing = await db.courses.find_one({"id": id, "isActive": True})
    if not existing:
        raise HTTPException(404, "Course not found")
    
    # Validate knowledge point and question IDs
    if course.knowledgePointIds:
        valid_kps = await db.knowledge_points.find(
            {"id": {"$in": course.knowledgePointIds}, "isActive": True}
        ).to_list(None)
        if len(valid_kps) != len(course.knowledgePointIds):
            raise HTTPException(400, "Some knowledge point IDs are invalid or inactive")
    
    if course.questionIds:
        valid_questions = await db.questions.find(
            {"id": {"$in": course.questionIds}, "isActive": True}
        ).to_list(None)
        if len(valid_questions) != len(course.questionIds):
            raise HTTPException(400, "Some question IDs are invalid or inactive")
    
    course_dict = course.dict(exclude={"id"})
    course_dict["updatedAt"] = datetime.utcnow().isoformat()
    course_dict["isActive"] = True
    await db.courses.update_one({"id": id}, {"$set": course_dict})
    
    course_dict["id"] = id
    course_dict["knowledgePointIds"] = [
        {
            "id": kp["id"],
            "grade": kp["grade"],
            "strand": kp["strand"],
            "topic": kp["topic"],
            "skill": kp["skill"],
            "subKnowledgePoint": kp["subKnowledgePoint"]
        } for kp in valid_kps
    ] if course.knowledgePointIds else []
    course_dict["questionIds"] = [
        {
            "id": q["id"],
            "title": q["title"],
            "content": q["content"]
        } for q in valid_questions
    ] if course.questionIds else []
    
    return course_dict

@router.delete("/{id}")
async def delete_course(id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(403, "Only admins can delete courses")
    
    result = await db.courses.update_one(
        {"id": id, "isActive": True},
        {"$set": {"isActive": False, "updatedAt": datetime.utcnow().isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(404, "Course not found or already deleted")
    return {"message": "Course deleted successfully"}