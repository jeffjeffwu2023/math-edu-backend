# main.py
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

# MongoDB connection (async)
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

# Include routes
from routes import questions, students, assignments, ai, answers

app.include_router(questions.router, prefix="/api/questions")
app.include_router(students.router, prefix="/api/students")
app.include_router(assignments.router, prefix="/api/assignments")
app.include_router(answers.router, prefix="/api/answers")
app.include_router(ai.router, prefix="/api/ai")


@app.on_event("startup")
async def startup_event():
    print("MongoDB connected")

@app.on_event("shutdown")
async def shutdown_event():
    client.close()
    print("MongoDB connection closed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)