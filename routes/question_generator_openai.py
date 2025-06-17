# routes/question_generator_openai.py
import openai
import os
from fastapi import HTTPException
from .latex_parser import parse_json_content  # Relative import with package notation
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import uuid
from dotenv import load_dotenv
import json
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["math_edu_db"]

async def generate_question_openai(request, current_user):
    try:
        # Log request details
        logger.info(f"Generating question with criteria: {request.dict()}")

        # Prepare prompt for OpenAI
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
        logger.info(f"Prompt sent to OpenAI API: {prompt}")

        # API call to OpenAI
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            logger.error("OpenAI API key not configured")
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7
        )

        logger.info(f"OpenAI API response: {response}")
        raw_content = response.choices[0].message.content
        logger.info(f"Raw content from OpenAI: {raw_content}")

        # Parse the raw content using latex_parser
        parsed_result = parse_json_content(raw_content)
        parsed_data = json.loads(parsed_result)
        logger.info(f"Parsed OpenAI response: {parsed_result}")

        # Prepare question data for potential MongoDB save
        question_data = {
            "title": "Generated Question",
            "question": parsed_data["question"],  # Array of segments
            "correctAnswer": parsed_data["correctAnswer"],  # Array of answers
            "difficulty": request.difficulty,
            "topic": selected_topic,
            "knowledgePoints": [],
            "passValidation": False,
            "createdAt": datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat(),
            "isActive": True,
            "user_id": current_user["id"]
        }

        # Save to MongoDB if requested
        if request.save_to_db:
            question_data["id"] = str(uuid.uuid4())
            try:
                await db.questions.insert_one(question_data)
                logger.info(f"Question saved to MongoDB with ID: {question_data['id']}")
            except Exception as e:
                logger.error(f"MongoDB insert failed: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to save to MongoDB: {str(e)}")

        # Return the parsed response
        response_dict = {
            "question": parsed_data["question"],  # Array of segments
            "correctAnswer": parsed_data["correctAnswer"],  # Array of answers
            "difficulty": request.difficulty,
            "topic": selected_topic,
            "passValidation": False,
            "id": question_data["id"] if request.save_to_db else None
        }

        logger.info(f"Returning response from OpenAI: {response_dict}")
        return response_dict

    except openai.error.OpenAIError as e:
        logger.error(f"OpenAI API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating question: {str(e)}")