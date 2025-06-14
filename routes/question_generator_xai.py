from fastapi import HTTPException
import os
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from dotenv import load_dotenv
import uuid
import logging
import json
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

async def generate_question_xai(request, current_user):
    try:
        # Log request details
        logger.info(f"Generating question with criteria: {request.dict()}")

        # Prepare prompt for complex questions with clear separation
        topics = ["algebra", "geometry", "calculus"]
        selected_topic = request.topic if request.topic in topics else random.choice(topics)
        prompt = (
            f"Generate a complex math question with multiple paragraphs, including multiple equations and various complex math expressions "
            f"(e.g., fractions, exponents, integrals, matrices), with the following requirements: "
            f"difficulty level {request.difficulty}, topic {selected_topic}, "
            f"format the question and correct answer in LaTeX. "
            f"Return a JSON object with 'question' and 'correctAnswer' fields. "
            f"The 'question' should include at least two paragraphs with diverse mathematical content, and the 'correctAnswer' should be a separate field "
            f"containing only the solution in the format '$x=value,y=value$' (e.g., '$x=3,y=1$'). Do not include the correct answer within the question text itself. "
            f"Ensure the answer is mathematically accurate and suitable for a student at this level."
        )
        logger.info(f"Prompt sent to xAI API: {prompt}")

        # API call to xAI
        xai_api_key = os.getenv("XAI_API_KEY")
        if not xai_api_key:
            logger.error("xAI API key not configured")
            raise HTTPException(status_code=500, detail="xAI API key not configured")

        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            json={
                "model": "grok-3-latest",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "temperature": 0.7
            },
            headers={"Authorization": f"Bearer {os.getenv('XAI_API_KEY')}"},
            timeout=60
        )

        logger.info(f"xAI API response status: {response.status_code}")
        if response.status_code != 200:
            logger.error(f"xAI API failed with status {response.status_code}: {response.text}")
            raise HTTPException(status_code=response.status_code, detail=f"Failed to generate question: {response.text}")

        logger.info(f"xAI API response: {response.json()}")
        raw_content = response.json()["choices"][0]["message"]["content"]

        # Parse the inner JSON to extract question and correctAnswer
        try:
            parsed_content = json.loads(raw_content)
            #question_text = parsed_content.get("question", "").replace("\n", " ").strip()
            question_text = parsed_content.get("question", "")

            correct_answer = parsed_content.get("correctAnswer", "")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse inner JSON content: {e}, raw_content: {raw_content}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON format in xAI response: {e}")

        # Prepare question data for potential MongoDB save
        question_data = {
            "title": "Generated Question",  # Can be adjusted based on question_text if needed
            "content": question_text,  # Store only the question text
            "correctAnswer": correct_answer,  # Extracted separately
            "difficulty": request.difficulty,
            "topic": selected_topic,
            "knowledgePoints": [],
            "passValidation": False,  # Validation moved to frontend
            "createdAt": datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat(),
            "isActive": True,
        }

        # Save to DB if requested
        if request.save_to_db:
            question_data["id"] = str(uuid.uuid4())
            try:
                await db.questions.insert_one(question_data)
                logger.info(f"Question saved to MongoDB: {question_data}")
            except Exception as e:
                logger.error(f"MongoDB insert failed: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to save to MongoDB: {str(e)}")

        # Prepare response dictionary with parsed content
        response_dict = {
            "question": question_text,  # Only the question text
            "correctAnswer": correct_answer,  # Extracted separately
            "htmlContent": question_text,  # Only the question text for frontend rendering
            "difficulty": request.difficulty,
            "topic": selected_topic,
            "passValidation": False,  # Validation moved to frontend
            "id": question_data["id"] if request.save_to_db else None
        }

        logger.info(f"Returning response from xAI: {response_dict}")
        return response_dict

    except requests.exceptions.RequestException as e:
        logger.error(f"Network or API request error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating question: {str(e)}")