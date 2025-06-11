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

router = APIRouter(prefix="/api/ai_mistral", tags=["ai_mistral"])

class PromptRequest(BaseModel):
    prompt: str

@router.post("/mistral_evaluate")
async def evaluate_answer(request: PromptRequest):
    logger.info(f"Forwarding prompt to AI server: {request.prompt}")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{os.getenv('AI_SERVER_URL', 'http://localhost:8080')}/v1/chat/completions",
            json={"prompt": request.prompt},
            timeout=30
        )
        response.raise_for_status()
        logger.info(f"AI server response: {response.json()}")
        return response.json()
    


@router.post("/mistral")
async def call_mistral(request: PromptRequest):
    try:
        logger.info(f"Forwarding prompt to AI server: {request.prompt}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
            f"{os.getenv('AI_SERVER_URL', 'http://localhost:8080')}/v1/chat/completions",
            json={"prompt": request.prompt},
            timeout=30
        )
        response.raise_for_status()
        logger.info(f"AI server response: {response.json()}")
    
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


@router.post("/analyze-student/")
async def analyze_student(student_data: dict, target_audience: str = "student", language: str = "en"):
    student_id = student_data["studentId"]
    #language = "zh-CN"
    language_instruction = "Please respond in Chinese (Simplified)." if language == "zh-CN" else "Please respond in English."
    if target_audience == "parent":
        prompt = f"Generate a performance analysis for the parents of this student based on their answer history, category breakdown, difficulty breakdown, and time spent. Summarize their overall performance, highlight key strengths and areas for improvement in specific math categories and difficulty levels, and provide actionable advice for parents to support their child’s learning. Use a professional and supportive tone. {language_instruction}"
    else:
        prompt = f"Analyze this student's math performance based on their answer history, category breakdown, difficulty breakdown, and time spent. Identify their weaknesses and strengths, focusing on specific math categories and difficulty levels. Provide actionable advice to improve their weaknesses. {language_instruction}"
    #student_data["prompt"] = prompt

    try:
        logger.info(f"Forwarding prompt to AI server: {student_data}")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{os.getenv('AI_SERVER_URL', 'http://localhost:8080')}/v1/chat/completions",
                json={"prompt": f"{prompt}\n\nStudent Data: {student_data}"},
                timeout=30
            )
            logger.info(f"AI server response: {response.json()}")

            response.raise_for_status()
            analysis = response.json()["choices"][0]["message"]["content"]
            print(f"Grok response: {analysis}")
            await db.student_analyses.insert_one({
                "studentId": student_data["studentId"],
                "targetAudience": target_audience,
                "language": language,
                "analysis": analysis,
                "timestamp": datetime.utcnow().isoformat()
            })
            return {"analysis": analysis}
    except httpx.HTTPStatusError as e:
        print(f"Grok API error: {e}")
        print(f"Response status: {e.response.status_code}, Response text: {e.response.text}")
        raise HTTPException(status_code=500, detail=f"Grok API error: {str(e)}")
    except httpx.RequestError as e:
        print(f"Network error while calling Grok API: {e}")
        print(f"Error details: {type(e).__name__}, {str(e)}")
        raise HTTPException(status_code=500, detail=f"Network error while calling Grok API: {str(e)}")