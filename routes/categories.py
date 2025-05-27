# routes/categories.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter(prefix="/api/categories", tags=["categories"])

class Category(BaseModel):
    name: str

@router.get("/")
async def get_categories():
    categories = await db.categories.find().to_list(None)
    return [{"name": cat["name"]} for cat in categories]

@router.post("/")
async def add_category(category: Category):
    if await db.categories.find_one({"name": category.name}):
        raise HTTPException(400, "Category already exists")
    await db.categories.insert_one({"name": category.name})
    return {"name": category.name}

@router.put("/{name}")
async def update_category(name: str, category: Category):
    if await db.categories.find_one({"name": category.name}):
        raise HTTPException(400, "Category already exists")
    result = await db.categories.update_one(
        {"name": name}, {"$set": {"name": category.name}}
    )
    if result.modified_count == 0:
        raise HTTPException(404, "Category not found")
    return {"name": category.name}

@router.delete("/{name}")
async def delete_category(name: str):
    if await db.categories.count_documents({}) <= 1:
        raise HTTPException(400, "At least one category must exist")
    result = await db.categories.delete_one({"name": name})
    if result.deleted_count == 0:
        raise HTTPException(404, "Category not found")
    return {"message": "Category deleted"}