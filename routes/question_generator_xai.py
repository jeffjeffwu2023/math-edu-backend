import json
import re
import httpx
from fastapi import HTTPException
import logging
import os
import sys

from routes.latex_parser import parse_mixed_content_with_original  # Import only necessary functions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dynamically adjust path to include the routes directory relative to the script location
script_dir = os.path.dirname(os.path.abspath(__file__))
routes_dir = os.path.join(script_dir, '..')  # Move up to the routes directory
sys.path.insert(0, routes_dir)  # Insert at the beginning to prioritize this path

# Updated utility functions
def replace_dollar_number(text):
    """
    Replace all occurrences of a dollar sign ($) immediately followed by a digit
    with '_CMD_DOLLAR_' in the given string.
    Args:
        text (str): The input string.
    Returns:
        str: The modified string with replacements.
    """
    return re.sub(r'\$\d', lambda m: '_CMD_DOLLAR_' + m.group(0)[1], text)

def replace_latex_inline_pairs(text, start_delimiter, end_delimiter, new_start_delimiter, new_end_delimiter):
    """
    Find all pairs of start and end delimiters in the text and replace them with
    '_FLG_LATEX_INLINE_START_' and '_FLG_LATEX_INLINE_END_'.
    Handles identical delimiters (e.g., '$') without nesting support.
    Args:
        text (str): The input string.
        start_delimiter (str): The starting delimiter (default: '\(').
        end_delimiter (str): The ending delimiter (default: '\)').
    Returns:
        str: The modified string with replacements.
    """
    result = []
    i = 0
    in_delimiter = False
    while i < len(text):
        if text[i:i+len(start_delimiter)] == start_delimiter and not in_delimiter:
            result.append("_FLG_LATEX_INLINE_START_")
            in_delimiter = True
            start_pos = i + len(start_delimiter)
            i += len(start_delimiter)
        elif text[i:i+len(end_delimiter)] == end_delimiter and in_delimiter:
            result.append(text[start_pos:i])
            result.append("_FLG_LATEX_INLINE_END_")
            in_delimiter = False
            i += len(end_delimiter)
        else:
            if not in_delimiter:
                result.append(text[i])
            i += 1
    # Handle any remaining unmatched start delimiter
    if in_delimiter:
        result.append(text[start_pos:])
        logger.warning(f"Unmatched {start_delimiter} delimiter detected, treating remainder as text")
    return "".join(result)

def process_latex_in_text(content):
    """
    Process LaTeX content by transforming delimiters and commands to avoid parse errors.
    """
    content = replace_dollar_number(content)
    content = content.replace("\\n\\n", "_CMD_NEWLINE_")
    content = content.replace("\\n", "_CMD_NONE_")
    content = content.replace("\\\\", "\\")  # Preserve single backslashes
    # Replace "\[...\]" with _FLG_LATEX_BLOCK_START_..._FLG_LATEX_BLOCK_END_
    content = re.sub(r'\\\[(.*?)\\\]', r'_CMD_LATEX_BLOCK_CENTER_START-\1_CMD_LATEX_BLOCK_CENTER_END_', content)
    content = re.sub(r'\\([a-zA-Z]+)', r'_CMD_LATEX_\1', content)  # Mark LaTeX commands
    content = content.replace("\\", "_BACKSLASH_")  # Replace remaining backslashes
    # Replace $...$ with _FLG_LATEX_INLINE_START_..._FLG_LATEX_INLINE_END_
    content = replace_latex_inline_pairs(content, start_delimiter='$', end_delimiter='$', new_start_delimiter="_FLG_LATEX_INLINE_START_",new_end_delimiter="_FLG_LATEX_INLINE_END_")
    # Replace \(...\) with _FLG_LATEX_INLINE_START_..._FLG_LATEX_INLINE_END_
    content = replace_latex_inline_pairs(content, start_delimiter='\\(', end_delimiter='\\)', new_start_delimiter="_FLG_LATEX_INLINE_START_", new_end_delimiter="_FLG_LATEX_INLINE_END_")
    content = replace_latex_inline_pairs(content, start_delimiter='\\[', end_delimiter='\\]', new_start_delimiter="_FLG_LATEX_CENTER_START_", new_end_delimiter="_FLG_LATEX_CENTER_END_")
    # Replace \begin{...} and \end{...} with _FLG_LATEX_BLOCK_START_ and _FLG_LATEX_BLOCK_END_
    content = re.sub(r'\\begin\{([^}]+)\}', r'_FLG_LATEX_BLOCK_START_\1-', content)
    content = re.sub(r'\\end\{([^}]+)\}', r'_FLG_LATEX_BLOCK_END_\1-', content)
    # Replace \textbf{...} with _CMD_LATEX_TEXTBF_START_..._CMD_LATEX_TEXTBF_END_
    content = re.sub(r'\\textbf\{([^}]+)\}', r'_CMD_LATEX_TEXTBF_START_\1_CMD_LATEX_TEXTBF_END_', content)
    # Replace \frac{...}{...} with _CMD_LATEX_FRACTION_START-..._CMD_LATEX_FRACTION_END_
    content = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'_CMD_LATEX_FRACTION_START-\1_CMD_LATEX_FRACTION_END_\2-', content)
    # Replace \cdot with _CMD_LATEX_CDOT_
    content = content.replace('\\cdot', '_CMD_LATEX_CDOT_')
    # Replace \int with _CMD_LATEX_INT_
    content = content.replace('\\int', '_CMD_LATEX_INT_')
    # Replace \sum with _CMD_LATEX_SUM_
    content = content.replace('\\sum', '_CMD_LATEX_SUM_')   

    return content

# Function to handle xAI API call and parsing
async def generate_question_xai(request, current_user):
    """
    Generate a math question using the xAI API and parse the response.
    Args:
        request: Pydantic model containing difficulty, topic, save_to_db, and ai_provider.
        current_user: Dict containing user details from authentication.
    Returns:
        dict: Parsed question and correct answer.
    """
    import os
    from dotenv import load_dotenv
    load_dotenv()

    xai_api_key = os.getenv("XAI_API_KEY")
    if not xai_api_key:
        raise HTTPException(status_code=500, detail="xAI API key not configured")

    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {xai_api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"Generate a complex math question with fractions in multiple paragraphs, including multiple equations and various complex math expressions (e.g., fractions, exponents, integrals, matrices), with the following requirements: difficulty level {request.difficulty}, topic {request.topic if request.topic else 'random'}, format the question and correct answer in LaTeX. Return a JSON object with 'question' and 'correctAnswer' fields. The 'question' should include at least two paragraphs with diverse mathematical content, and the 'correctAnswer' should be a separate field containing only the solution in the format '$x=value,y=value$' (e.g., '$x=3,y=1$'). Do not include the correct answer within the question text itself. Ensure the answer is mathematically accurate and suitable for a student at this level."

    payload = {
        "model": "grok-3",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            logger.info(f"xAI API response: {data}")

            # Preprocess the raw content before parsing
            raw_content = data["choices"][0]["message"]["content"]
            raw_content = process_latex_in_text(raw_content)  # Apply transformations to avoid parse errors
            logger.info(f"Debug: Preprocessed raw_content: {raw_content}")

            # Parse the preprocessed content
            json_obj = json.loads(raw_content)
            logger.info(f"Debug: Raw JSON content: {json_obj}")

            # Use the original transformed content for parsing, avoiding reprocessing
            parsed_data = {
                "question": parse_mixed_content_with_original(json_obj["question"]),
                "correctAnswer": parse_mixed_content_with_original(json_obj["correctAnswer"])
            }
            logger.info(f"Parsed xAI response: {parsed_data}")

            return parsed_data  # Return dictionary directly to match response_model=dict
        except httpx.HTTPStatusError as e:
            logger.error(f"xAI API error: {str(e)}")
            raise HTTPException(status_code=e.response.status_code, detail=f"xAI API request failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to decode xAI response: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error processing xAI response: {str(e)}")
