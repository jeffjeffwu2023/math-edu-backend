from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os
import requests
from sympy import sympify, latex, S
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from routes.auth import get_current_user
import random
from dotenv import load_dotenv
import uuid
import json
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

router = APIRouter(prefix="/api/generate-question", tags=["question-generator"])

class GenerateQuestionRequest(BaseModel):
    difficulty: str  # "easy", "medium", "hard"
    topic: str = None  # "algebra", "geometry", "calculus", or None for random
    save_to_db: bool = False  # Option to save to MongoDB
    ai_provider: str = None  # New field to switch between providers, default to grok

@router.post("/", response_model=dict)
async def generate_question(request: GenerateQuestionRequest, current_user: dict = Depends(get_current_user)):
    try:
        # Log request details
        logger.info(f"Generating question with criteria: {request.dict()}")

        # Prepare prompt
        topics = ["algebra", "geometry", "calculus"]
        selected_topic = request.topic if request.topic in topics else random.choice(topics)
        prompt = f"Generate a multiple equations math question with the following requirements: difficulty level {request.difficulty}, topic {selected_topic}, format the question and correct answer in LaTeX. Return a JSON object with 'question' and 'correctAnswer' fields. Ensure the answer is mathematically accurate and suitable for a student at this level."
        logger.info(f"Prompt sent to AI API: {prompt}")
        logger.info(f"request.ai_provider: {request.ai_provider}")

        # API call based on provider
        if request.ai_provider == "grok":
            xai_api_key = os.getenv("XAI_API_KEY")
            if not xai_api_key:
                logger.error("xAI API key not configured")
                raise HTTPException(status_code=500, detail="xAI API key not configured")

            response = requests.post(
                "https://api.x.ai/v1/chat/completions",  # Replace with actual endpoint from https://x.ai/api
                json={
                    "model": "grok-3-latest",
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "temperature": 0.7
                },
                headers={"Authorization": f"Bearer {os.getenv('XAI_API_KEY')}"},
                timeout=30
            )

            logger.info(f"xAI API response status: {response.status_code}")
            logger.info(f"xAI API response status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"xAI API failed with status {response.status_code}: {response.text}")
                raise HTTPException(status_code=response.status_code, detail=f"Failed to generate question: {response.text}")

            result = response.json()
            content = result["choices"][0]["message"]["content"]

        elif request.ai_provider == "openai":
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                logger.error("OpenAI API key not configured")
                raise HTTPException(status_code=500, detail="OpenAI API key not configured")

            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                json={
                    "model": "gpt-4",  # Adjust model as needed (e.g., gpt-4)
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "temperature": 0.7
                },
                headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
                timeout=30
            )
            logger.info(f"OpenAI API response status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"OpenAI API failed with status {response.status_code}: {response.text}")
                raise HTTPException(status_code=response.status_code, detail=f"Failed to generate question: {response.text}")

            result = response.json()
            content = result["choices"][0]["message"]["content"]

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported AI provider: {request.ai_provider}")

        logger.info(f"Extracted content: {content}")
        try:
            parsed_result = json.loads(content)
            logger.info(f"Parsed JSON: {parsed_result}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from content: {content}, error: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON format in response: {str(e)}")

        # Validate the parsed response
        if not parsed_result.get("question") or not parsed_result.get("correctAnswer"):
            logger.error(f"Invalid parsed response format: {parsed_result}")
            raise HTTPException(status_code=400, detail="Invalid response from AI")

        # Enhanced SymPy validation to handle LaTeX solutions
        pass_validation = False
        correct_answer_text = parsed_result["correctAnswer"]
        math_expr = re.sub(r'\\\(|\\\)', '', correct_answer_text).strip()
        try:
            sympified_expr = sympify(math_expr)
            if isinstance(sympified_expr, S.Number) or sympified_expr.free_symbols:
                pass_validation = True
            logger.info(f"SymPy validation passed for: {math_expr}")
        except Exception as e:
            logger.warning(f"SymPy validation failed for {math_expr}: {str(e)}")

        # Prepare question data for potential MongoDB save
        question_data = {
            "title": parsed_result["question"].split("\\text{")[1].split("}")[0][:50] if "\\text{" in parsed_result["question"] else "Generated Question",
            "content": parsed_result["question"],
            "correctAnswer": parsed_result["correctAnswer"],
            "difficulty": request.difficulty,
            "topic": selected_topic,
            "knowledgePoints": [],
            "passValidation": pass_validation,
            "createdAt": datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat(),
            "isActive": True,
        }

        if request.save_to_db:
            question_data["id"] = str(uuid.uuid4())
            try:
                await db.questions.insert_one(question_data)
                logger.info(f"Question saved to MongoDB: {question_data}")
            except Exception as e:
                logger.error(f"MongoDB insert failed: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to save to MongoDB: {str(e)}")

        return {
            "question": parsed_result["question"],
            "correctAnswer": parsed_result["correctAnswer"],
            "passValidation": pass_validation,
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Network or API request error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating question: {str(e)}")
