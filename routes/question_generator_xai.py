import json
import re
import httpx
from fastapi import HTTPException
import logging
from routes.latex_parser import parse_json_content  # Import the missing function

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



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

def replace_latex_inline_pairs(text, start_delimiter='\\(', end_delimiter='\\)'):
    """
    Find all '\(' and '\)' pairs in the text and replace them with
    '-CMD_LATEX_INLINE_START-' and '-CMD_LATEX_INLINE_END-'.
    If no pairs are found, the text is returned unchanged.
    """
    result = []
    i = 0
    while i < len(text):
        if text[i:i+2] == start_delimiter:
            result.append("-CMD_LATEX_INLINE_START-")
            i += 2
            # Find the matching \)
            start = i
            while i < len(text):
                if text[i:i+2] == end_delimiter:
                    result.append(text[start:i])
                    result.append("-CMD_LATEX_INLINE_END-")
                    i += 2
                    break
                i += 1
            else:
                # No matching \), treat as normal text
                result.append(text[start:])
                break
        else:
            result.append(text[i])
            i += 1
    return "".join(result)


def process_latex_in_text(content):
    # replace "\\" with "\"
    content = content.replace("\\\\", "\\")
    # replace "\" with "-BACKSLASH-"
    content = content.replace("\\", "-BACKSLASH-")

    def replacer(match):
        latex = match.group(0)

        # Remove delimiters for processing
        if latex.startswith('$') and latex.endswith('$'):
            inner = latex[1:-1].strip()
        elif latex.startswith('\\(') and latex.endswith('\\)'):
            inner = latex[2:-2].strip()
        elif latex.startswith('\\[') and latex.endswith('\\]'):
            inner = latex[2:-2].strip()
        else:
            inner = latex.strip()

        # Prefix
        prefix = "-CMD-LATEX-START-"

        # Replace starting \ with -BACKSLASH-
        if inner.startswith('\\'):
            inner = '-BACKSLASH-' + inner[1:]

        # Replace all LaTeX commands \command{...} or \command
        def cmd_replacer(m):
            cmd = m.group(1)
            arg = m.group(2) if m.group(2) else ""
            return f"-CMD-LATEX-{cmd}{arg}"

        # Replace commands and consume leading \
        inner = re.sub(r'\\([a-zA-Z]+)(\{[^}]*\})?', cmd_replacer, inner)

        # Replace \end{...} at end → -CMD-LATEX-END-end{...}
        inner, count = re.subn(
            r'-CMD-LATEX-end(\{[^}]+\})\s*$',
            r'-CMD-LATEX-END-end\1',
            inner
        )

        # If no \end matched, append -CMD-LATEX-END-
        if count == 0:
            inner += '-CMD-LATEX-END-'

        return prefix + inner

    # Pattern for inline math, display math, environments
    pattern = r'(\$.*?\$|\\\(.*?\\\)|\\\[.*?\\\]|\\begin\{[^}]*\}.*?\\end\{[^}]*\})'

    result = re.sub(pattern, replacer, content, flags=re.DOTALL)
    return result




# Existing functions remain unchanged
def clean_latex_value(latex_str):
    """
    Clean LaTeX commands from the value field, retaining only the content.
    Args:
        latex_str (str): The raw LaTeX string to clean.
    Returns:
        str: The cleaned content with LaTeX commands removed.
    """
    cleaned = re.sub(r'\\textbf\{([^}]*)\}', r'\1', latex_str)  # Remove \textbf{...}
    cleaned = re.sub(r'\\begin\{[^}]*\}|\end\{[^}]*\}', r'', cleaned)  # Remove \begin{...} and \end{...}
    cleaned = re.sub(r'\\frac\{[^}]*\}\{[^}]*\}', r'', cleaned)  # Remove \frac{...}{...} (placeholder)
    cleaned = re.sub(r'\\[a-zA-Z]+ *', r'', cleaned)  # Remove other LaTeX commands (e.g., \cdot, \int)
    cleaned = cleaned.strip()
    return cleaned if cleaned else latex_str

def parse_mixed_content_with_original(content):
    """
    Parse a string into an array of text and LaTeX segments, preserving original LaTeX for comparison.
    Args:
        content (str): The input string containing mixed text and LaTeX.
    Returns:
        list: Array of objects with {value: string, type: "text" | "latex", original_latex: string | None}.
              - 'value' is the processed content (for $...$ with math expressions, delimiters removed and commands cleaned;
                for \\(...\\) and \\begin{...}, full original with commands cleaned; others as text).
              - 'type' is "text" or "latex".
              - 'original_latex' is the original LaTeX string (including delimiters) for latex type, None for text.
    """
    if not content or not isinstance(content, str):
        return [{"value": "", "type": "text", "original_latex": None}]
    
    result = []
    current_pos = 0
    i = 0
    dollar_count = 0  # Track nested $ delimiters
    
    while i < len(content):
        # Check for $...$ (inline math)
        if content[i] == '$':
            if dollar_count == 0 and current_pos < i:
                result.append({"value": content[current_pos:i].strip(), "type": "text", "original_latex": None})
            dollar_count += 1
            if dollar_count == 1:
                start = i
            i += 1
            while i < len(content) and dollar_count > 0:
                if content[i] == '$':
                    dollar_count -= 1
                    if dollar_count == 0 and i > start:
                        original_latex = content[start:i + 1].strip()
                        inner_content = original_latex[1:-1].strip()
                        if inner_content and not inner_content.isspace():
                            latex_value = clean_latex_value(inner_content)  # Clean LaTeX commands
                            print(f"Debug: $...$ - original_latex='{original_latex}', latex_content='{inner_content}', cleaned_value='{latex_value}' (parsed as math)")
                            result.append({"value": latex_value, "type": "latex", "original_latex": original_latex})
                        else:
                            print(f"Debug: $...$ - original_latex='{original_latex}' skipped (empty or whitespace)")
                            result.append({"value": original_latex, "type": "text", "original_latex": None})
                        current_pos = i + 1
                i += 1
            if dollar_count > 0:
                print(f"Debug: Unmatched $ at position {i}, treating remainder as text")
                result.append({"value": content[current_pos:].strip(), "type": "text", "original_latex": None})
                break
        # Check for $$...$$ (display math)
        elif content[i:i+2] == '$$':
            if current_pos < i:
                result.append({"value": content[current_pos:i].strip(), "type": "text", "original_latex": None})
            start = i
            i += 2
            while i < len(content) and content[i:i+2] != '$$':
                i += 1
            if i < len(content) and content[i:i+2] == '$$':
                original_latex = content[start:i + 2].strip()
                latex_content = original_latex[2:-2].strip()
                latex_value = clean_latex_value(latex_content)  # Clean LaTeX commands
                print(f"Debug: $$...$$ - original_latex='{original_latex}', latex_content='{latex_content}', cleaned_value='{latex_value}'")
                result.append({"value": latex_value, "type": "latex", "original_latex": original_latex})
                current_pos = i + 2
            i += 2
        # Check for \(...\), \(...\), or \\(...\\) (inline/display math)
        elif content[i:i+2] == '\\(' or (i > 0 and content[i-1:i+1] == '\\\\('):
            if current_pos < i:
                result.append({"value": content[current_pos:i].strip(), "type": "text", "original_latex": None})
            start = i if content[i:i+2] == '\\(' else i - 1
            i += 2 if content[i:i+2] == '\\(' else 3  # Skip \( or \\(
            while i < len(content) and content[i:i+2] != '\\)' and (i < len(content) - 1 or content[i] != '\\'):
                i += 1
            if i < len(content) and content[i:i+2] == '\\)':
                original_latex = content[start:i + 2].strip()
                latex_content = original_latex  # Use full original LaTeX including delimiters
                print(f"Debug: \\(...\\) - original_latex='{original_latex}', latex_content='{latex_content}'")
                result.append({"value": latex_content, "type": "latex", "original_latex": original_latex})
                current_pos = i + 2
            i += 2
        # Check for \begin{...}...\end{...} (e.g., align environment)
        elif content[i:i+7].lower() == '\\begin{' and i + 7 < len(content):
            if current_pos < i:
                result.append({"value": content[current_pos:i].strip(), "type": "text", "original_latex": None})
            start = i
            env_name = ""
            j = i + 7
            while j < len(content) and content[j] != '}':
                env_name += content[j]
                j += 1
            if j < len(content) and content[j] == '}':
                env_end = f'\\end{{{env_name}}}'
                i = j + 1
                while i < len(content) - len(env_end) + 1:
                    if content[i:i+len(env_end)] == env_end:
                        original_latex = content[start:i + len(env_end)].strip()
                        latex_content = original_latex  # Keep full LaTeX for environments
                        print(f"Debug: \\begin{...} - original_latex='{original_latex}', latex_content='{latex_content}'")
                        result.append({"value": latex_content, "type": "latex", "original_latex": original_latex})
                        current_pos = i + len(env_end)
                        break
                    i += 1
                else:
                    i = start + 1
            else:
                i += 1
        else:
            i += 1
    
    if current_pos < len(content):
        result.append({"value": content[current_pos:].strip(), "type": "text", "original_latex": None})
    
    return result

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
            #replace all "\\n\\n"   with "[CMD_NEWLINE]"
            raw_content = raw_content.replace("\\n\\n", "_CMD_NEWLINE_")
            #replace all "\n" with ""
            raw_content = raw_content.replace("\\n", "_CMD_NONE_")

            raw_content = replace_dollar_number(raw_content)  # Replace $x with _CMD_DOLLAR_x   
            
            #  find "\(" and "\)" pair and replace them with "-CMD_LATEX_INLINE_START-" and "-CMD_LATEX_INLINE_END-"


            #  find "\(" and "\)" pair and replewith "-CMD_LATEX_INLINE_START-" and "-CMD_LATEX_INLINE_END-"
            # raw_content = raw_content.replace("\\(", "-CMD_LATEX_INLINE_START-")
            # raw_content = raw_content.replace("\\)", "-CMD_LATEX_INLINE_END-")
            logger.info(f"Raw content from xAI: {raw_content}")

            raw_content = process_latex_in_text(raw_content)  # Process LaTeX content
            logger.info(f"Processed raw content for LaTeX: {raw_content}")
            
            # Parse if the content is a valid JSON string
            if isinstance(raw_content, str):
                logger.info(f"Debug: Raw content is a string, attempting to parse: {raw_content}")
            else:
                logger.info(f"Debug: Raw content is not a string, using as is: {raw_content}")

            #raw_content == replace_latex_inline_pairs(raw_content,"\\(", "\\)")  # Ensure LaTeX inline pairs are replaced correctly
            #raw_content == replace_latex_inline_pairs(raw_content,"$", "$")  # Ensure LaTeX inline pairs are replaced correctly
            logger.info(f"Processed raw content for JSON parsing: {raw_content}")

            json_obj = json.loads(raw_content)
            logger.info(f"Debug: Raw JSON content: {json_obj}")
            
            """
            try:
                # Attempt to parse directly first
                json_obj = json.loads(raw_content)
            except json.JSONDecodeError as e:
                print(f"Debug: Initial parse failed: {str(e)}")
                # Preprocess to escape invalid sequences
                json_str = re.sub(r'\\\$', r'\\\\$', raw_content)  # Convert \$ to \\$ for JSON
                json_str = re.sub(r'(?<!\\)(?![nrt"\\])\\([eEfF])', r'\\\\\1', json_str, flags=re.DOTALL)  # Handle \e, \f, etc.
                print(f"Debug: Preprocessed raw_json: {json_str}")  # Debug the preprocessed string
                json_obj = json.loads(json_str)
"""
           
            # Parse the processed content
            parsed_data = parse_json_content(json_obj)  # Now properly imported
            logger.info(f"Parsed xAI response: {parsed_data}")

            return json.loads(parsed_data)
        except httpx.HTTPStatusError as e:
            logger.error(f"xAI API error: {str(e)}")
            raise HTTPException(status_code=e.response.status_code, detail=f"xAI API request failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to decode xAI response: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error processing xAI response: {str(e)}")
        

if __name__ == "__main__":
    text = (
        'Inline: $\\frac{x}{2} + y$. '
        'Block: \\begin{align} x + y = 1 \\\\ z = 2 \\end{align}.'
    )

    processed = process_latex_in_text(text)
    print(processed)
