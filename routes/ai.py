# routes/ai.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import os
from dotenv import load_dotenv
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import logging
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter()

class PromptRequest(BaseModel):
    prompt: str

@router.post("/grok")
async def call_grok(request: PromptRequest):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.x.ai/v1/chat/completions",
                json={
                    "model": "grok-3-latest",
                    "messages": [{"role": "user", "content": request.prompt}],
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 100
                },
                headers={"Authorization": f"Bearer {os.getenv('XAI_API_KEY')}"}
            )
            response.raise_for_status()
            logger.info(f"Grok API response: {response.json()}")

            response_data = response.json()
            if "choices" not in response_data or not response_data["choices"]:
                logger.error("Grok API response missing 'choices' field")
                raise ValueError("Grok API response missing 'choices' field")
            
            choice = response_data["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                answer = choice["message"]["content"]
            elif "text" in choice:
                answer = choice["text"]
            elif "content" in choice:
                answer = choice["content"]
            else:
                logger.error("Grok API response missing expected content field")
                raise ValueError("Grok API response missing expected content field")

            return {"answer": answer}
    except httpx.HTTPStatusError as e:
        error_detail = e.response.json() if e.response.content else str(e)
        logger.error(f"Grok API HTTP error: {error_detail}")
        if e.response.status_code == 404:
            return {"answer": f"Mock response from Grok: I would help with your prompt '{request.prompt}', but the API endpoint is not found. Please check the correct endpoint in xAI documentation."}
        raise HTTPException(status_code=500, detail=f"Error from Grok API: {error_detail}")
    except httpx.RequestError as e:
        logger.error(f"Grok API request error: {str(e)}\nTraceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Grok API request error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in call_grok: {str(e)}\nTraceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.post("/analyze-student")
async def analyze_student(student_data: dict, target_audience: str = "student", language: str = "en"):
    try:
        student_id = student_data["studentId"]
        logger.info(f"Analyzing student {student_id} for {target_audience} in language {language}")
        
        language_instruction = "Please respond in Chinese (Simplified)." if language == "zh-CN" else "Please respond in English."
        if target_audience == "parent":
            prompt = f"Generate a performance analysis for the parents of this student based on their answer history, category breakdown, difficulty breakdown, and time spent. Summarize their overall performance, highlight key strengths and areas for improvement in specific math categories and difficulty levels, and provide actionable advice for parents to support their child’s learning. Use a professional and supportive tone. {language_instruction}"
        else:
            prompt = f"Analyze this student's math performance based on their answer history, category breakdown, difficulty breakdown, and time spent. Identify their weaknesses and strengths, focusing on specific math categories and difficulty levels. Provide actionable advice to improve their weaknesses. {language_instruction}"
        student_data["prompt"] = prompt

        async with httpx.AsyncClient(timeout=30.0) as client:  # Added timeout
            response = await client.post(
                "https://api.x.ai/v1/chat/completions",
                json={
                    "model": "grok-3-latest",
                    "messages": [
                        {"role": "user", "content": f"{prompt}\n\nStudent Data: {student_data}"}
                    ],
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 500
                },
                headers={"Authorization": f"Bearer {os.getenv('XAI_API_KEY')}"}
            )
            response.raise_for_status()
            logger.info(f"Grok API response: {response.json()}")

            response_data = response.json()
            if "choices" not in response_data or not response_data["choices"]:
                logger.error("Grok API response missing 'choices' field")
                raise ValueError("Grok API response missing 'choices' field")
            
            choice = response_data["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                analysis = choice["message"]["content"]
            elif "text" in choice:
                analysis = choice["text"]
            elif "content" in choice:
                analysis = choice["content"]
            else:
                logger.error("Grok API response missing expected content field")
                raise ValueError("Grok API response missing expected content field")

            try:
                await db.student_analyses.insert_one({
                    "studentId": student_data["studentId"],
                    "targetAudience": target_audience,
                    "language": language,
                    "analysis": analysis,
                    "timestamp": datetime.utcnow().isoformat()
                })
                logger.info(f"Saved analysis for student {student_id}")
            except Exception as mongo_error:
                logger.error(f"MongoDB error while saving analysis: {str(mongo_error)}\nTraceback: {traceback.format_exc()}")
                raise HTTPException(status_code=500, detail=f"MongoDB error: {str(mongo_error)}")

            return {"analysis": analysis}
    except httpx.HTTPStatusError as e:
        error_detail = e.response.json() if e.response.content else str(e)
        logger.error(f"Grok API HTTP error: {error_detail}")
        if e.response.status_code == 404:
            return {"analysis": f"Mock response from Grok: I would analyze the student data, but the API endpoint is not found. Please check the correct endpoint in xAI documentation."}
        raise HTTPException(status_code=500, detail=f"Error from Grok API: {error_detail}")
    except httpx.RequestError as e:
        logger.error(f"Grok API request error: {str(e)}\nTraceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Grok API request error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in analyze_student: {str(e)}\nTraceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")