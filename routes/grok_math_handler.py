import httpx
import json
import os
import base64
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()
xai_api_key = os.getenv("XAI_API_KEY")
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def call_grok_api(prompt):
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {xai_api_key}", "Content-Type": "application/json"}
    payload = {"model": "grok-3", "messages": [{"role": "user", "content": prompt}], "max_tokens": 2000}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

def double_newline_to_paragraph(result):
    for key in ["question", "correctAnswer"]:
        if key in result and isinstance(result[key], list):
            new_items = []
            prev_newline = False
            for item in result[key]:
                if item["type"] == "newline":
                    new_items.append(item)
                    new_items.append(item)
                else:
                    new_items.append(item)
            result[key] = new_items
    return result

async def process_math_question(request: BaseModel):
    # Precompute the base64 example with escaped backslashes
    base64_example = base64.b64encode(b'\\int_0^1 x \\, dx').decode()
    logger.info(f"Base64 example computed: {base64_example}")
    # Precompute the example string to avoid f-string formatting issues
    example = json.dumps({
        "question": [
            {'type': 'text', 'value': 'Evaluate the integral '},
            {'type': 'latex', 'value': base64_example},
            {'type': 'newline', 'value': ''},
            {'type': 'text', 'value': 'Consider the next step '}
        ],
        "correctAnswer": [{'type': 'latex', 'value': base64_example}]
    })
    prompt = f"Generate a {request.difficulty} math question with an integral, a fraction, a matrix, a sum, and a limit, mixed with explanatory text across multiple paragraphs in the 'question' field. Return a JSON object with 'question' and 'correctAnswer' fields, each a JSON array where each element has 'type' ('text', 'latex', or 'newline') and 'value'. Use 'text' for plain text, 'latex' for LaTeX expressions (encoded in base64), and 'newline' for paragraph breaks in 'question'. For 'correctAnswer', provide only the final answer as a single 'latex' or 'text' element, encoded in base64. Example: {example}."
    logger.info(f"Using prompt: {prompt}")
    response = await call_grok_api(prompt)
    result = json.loads(response)
    # For every single 'newline', convert to two consecutive 'newline' elements
    for key in ["question", "correctAnswer"]:
        if key in result and isinstance(result[key], list):
            new_items = []
            for item in result[key]:
                if item["type"] == "newline":
                    new_items.append(item)
                    new_items.append({"type": "newline", "value": ""})
                else:
                    new_items.append(item)
            result[key] = new_items
    logger.info(f"Raw response: {result}")
    # Process each array within the dictionary
    for key in ["question", "correctAnswer"]:
        if key in result and isinstance(result[key], list):
            for item in result[key]:
                if item["type"] == "latex":
                    try:
                        original_value = item["value"]  # Store original base64
                        item["value"] = base64.b64decode(item["value"].encode()).decode()  # Decode to value
                        item["value64"] = original_value  # Assign original base64 to value64
                        logger.debug(f"Decoded item in {key}: {item}")
                    except base64.binascii.Error as e:
                        logger.error(f"Base64 decoding error for item {item} in {key}: {e}")
                        item["value"] = "Decoding Error"
                        item["value64"] = item.get("value", "")
                elif item["type"] == "newline":
                    logger.debug(f"Found newline in {key}: {item}")
    # Ensure correctAnswer contains only the final answer
    if "correctAnswer" in result and len(result["correctAnswer"]) > 1:
        logger.warning(f"Multiple segments in correctAnswer, keeping only the last one: {result['correctAnswer']}")
        result["correctAnswer"] = [result["correctAnswer"][-1]]  # Keep only the last segment
    logger.info(f"Processed result: {result}")
    return result

# Example usage
import asyncio
if __name__ == "__main__":
    # Simulate a request for testing
    class MockRequest(BaseModel):
        difficulty: str = "medium"
        topic: str = "calculus"
    asyncio.run(process_math_question(MockRequest()))