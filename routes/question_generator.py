from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os
import requests
from sympy import sympify, latex
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from routes.auth import get_current_user
import random
from dotenv import load_dotenv
import uuid
import json
import logging

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

@router.post("/", response_model=dict)
async def generate_question(request: GenerateQuestionRequest, current_user: dict = Depends(get_current_user)):
    try :
        logger.info(f"Generating question with criteria: {request.dict()}")

        # xAI API configuration
        xai_api_key = os.getenv("XAI_API_KEY")
        if not xai_api_key:
            logger.error("xAI API key not configured")
            raise HTTPException(status_code=500, detail="xAI API key not configured")

        # Prepare prompt
        topics = ["algebra", "geometry", "calculus"]
        selected_topic = request.topic if request.topic in topics else random.choice(topics)
        prompt = f"Generate a math question with the following requirements: difficulty level {request.difficulty}, topic {selected_topic}, format the question and correct answer in LaTeX. Return a JSON object with 'question' and 'correctAnswer' fields. Ensure the answer is mathematically accurate and suitable for a student at this level."
        logger.info(f"Prompt sent to xAI API: {prompt}")

        # Call xAI API
        response = requests.post(
            "https://api.x.ai/v1/chat/completions",  # Replace with actual endpoint from https://x.ai/api
            json={
                "model": "grok-3-latest",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "temperature": 0.7,
                "max_tokens": 100
            },
            headers={"Authorization": f"Bearer {os.getenv('XAI_API_KEY')}"},
            timeout=30  # Add timeout to prevent hanging
        )

        logger.info(f"xAI API response status: {response.status_code}")
        if response.status_code != 200:
            logger.error(f"xAI API failed with status {response.status_code}: {response.text}")
            raise HTTPException(status_code=response.status_code, detail=f"Failed to generate question: {response.text}")

        result = response.json()
        logger.info(f"xAI API raw response data: {result}")

        # Extract and parse the JSON string from choices[0].message.content
        if not result.get("choices") or len(result["choices"]) == 0:
            logger.error(f"No choices in response: {result}")
            raise HTTPException(status_code=400, detail="No choices in xAI response")

        content = result["choices"][0]["message"]["content"]
        logger.info(f"Extracted content: {content}")
        try :
            parsed_result = json.loads(content)
            logger.info(f"Parsed JSON: {parsed_result}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from content: {content}, error: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON format in response: {str(e)}")

        # Validate the parsed response
        if not parsed_result.get("question") or not parsed_result.get("correctAnswer"):
            logger.error(f"Invalid parsed response format: {parsed_result}")
            raise HTTPException(status_code=400, detail="Invalid response from AI")

        # Validate answer with SymPy
        pass_validation = False
        try :
            sympify(parsed_result["correctAnswer"])  # Basic validation
            pass_validation = True
            logger.info("SymPy validation passed")
        except Exception as e:
            logger.warning(f"SymPy validation failed: {str(e)}")

        # Prepare question data for potential MongoDB save
        question_data = {
            "title": parsed_result["question"].split("\\text{")[1].split("}")[0][:50] if "\\text{" in parsed_result["question"] else "Generated Question",
            "content": parsed_result["question"],
            "correctAnswer": parsed_result["correctAnswer"],  # Added field
            "difficulty": request.difficulty,
            "topic": selected_topic,
            "knowledgePoints": [],  # Can be populated later in AddQuestion.jsx
            "passValidation": pass_validation,  # Added field
            "createdAt": datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat(),
            "isActive": True,
        }

        # Optionally save to MongoDB
        if request.save_to_db:
            question_data["id"] = str(uuid.uuid4())  # Generate UUID
            try :
                await db.questions.insert_one(question_data)
                logger.info(f"Question saved to MongoDB: {question_data}")
            except Exception as e:
                logger.error(f"MongoDB insert failed: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to save to MongoDB: {str(e)}")

        return {
            "question": parsed_result["question"],
            "correctAnswer": parsed_result["correctAnswer"],
            "passValidation": pass_validation,  # Return validation status
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Network or API request error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating question: {str(e)}")
