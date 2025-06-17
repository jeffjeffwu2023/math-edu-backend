import json
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_latex_value(latex_str):
    return latex_str
    """
    Clean LaTeX commands from the value field, retaining only the content.
    Args:
        latex_str (str): The raw LaTeX string to clean.
    Returns:
        str: The cleaned content with LaTeX commands removed.
    """
    # Use raw strings for regex patterns to avoid deprecation warnings
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
                            logger.info(f"Debug: $...$ - original_latex='{original_latex}', latex_content='{inner_content}', cleaned_value='{latex_value}' (parsed as math)")
                            result.append({"value": latex_value, "type": "latex", "original_latex": original_latex})
                        else:
                            logger.info(f"Debug: $...$ - original_latex='{original_latex}' skipped (empty or whitespace)")
                            result.append({"value": original_latex, "type": "text", "original_latex": None})
                        current_pos = i + 1
                i += 1
            if dollar_count > 0:
                logger.info(f"Debug: Unmatched $ at position {i}, treating remainder as text")
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
                logger.info(f"Debug: $$...$$ - original_latex='{original_latex}', latex_content='{latex_content}', cleaned_value='{latex_value}'")
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
                logger.info(f"Debug: \\(...\\) - original_latex='{original_latex}', latex_content='{latex_content}'")
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
                        logger.info(f"Debug: \\begin{...} - original_latex='{original_latex}', latex_content='{latex_content}'")
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

def parse_json_content(raw_json):
    logger.info(f"Parsing raw JSON content: {raw_json}")
                
    """
    Parse a JSON object containing 'question' and 'correctAnswer' fields into a structured format.
    Args:
        raw_json (str or dict): The input JSON string or object containing 'question' and 'correctAnswer'.
    Returns:
        str: JSON-formatted string with 'question' and 'correctAnswer' as arrays of {value, type, original_latex} objects.
    """
    try:
        # Preprocess raw JSON to ensure valid parsing
        if isinstance(raw_json, str):
            logger.info(f"Debug: Raw JSON is a string, attempting to parse: {raw_json}")
            # Preprocess before initial parse attempt
            json_str = re.sub(r'\\\$', r'\\\\$', raw_json)  # Convert \$ to \\$ for JSON
            json_str = re.sub(r'\\([a-zA-Z])', r'\\\\\1', json_str, flags=re.DOTALL)  # Handle all LaTeX commands, including \e
            logger.info(f"Debug: Preprocessed raw_json: {json_str}")  # Debug the preprocessed string
            try:
                json_obj = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.info(f"Debug: Initial parse failed after preprocessing: {str(e)}")
                logger.error(f"Invalid JSON format after preprocessing: {str(e)}")
                raise  # Re-raise to handle in outer try block
        else:
            json_obj = raw_json


        # Parse question field
        question_text = json_obj.get("question", "")
        logger.info(f"Debug: Question text before parsing: {question_text}")
        question_segments = parse_mixed_content_with_original(question_text)
    

        # Parse correctAnswer field as a single LaTeX expression or multiple answers
        correct_answer_text = json_obj.get("correctAnswer", "")
        correct_answer_segments = []
        if correct_answer_text:
            # Treat the entire correctAnswer as a single LaTeX expression first
            if correct_answer_text.startswith('$') and correct_answer_text.endswith('$'):
                if ',' in correct_answer_text:
                    # Split only if comma is within $...$ and treat each part as a separate LaTeX expression
                    answers = [f"${part.strip()}$" for part in correct_answer_text[1:-1].split(',')]
                    for answer in answers:
                        inner_content = answer[1:-1].strip()
                        latex_value = clean_latex_value(inner_content)  # Clean LaTeX commands
                        correct_answer_segments.append({
                            "value": latex_value,
                            "type": "latex",
                            "original_latex": answer
                        })
                else:
                    # Single LaTeX expression
                    inner_content = correct_answer_text[1:-1].strip() if correct_answer_text.startswith('$') and correct_answer_text.endswith('$') else correct_answer_text
                    latex_value = clean_latex_value(inner_content)  # Clean LaTeX commands
                    correct_answer_segments.append({
                        "value": latex_value,
                        "type": "latex",
                        "original_latex": correct_answer_text
                    })
            else:
                # Non-LaTeX format, treat as text or single entry
                correct_answer_segments.append({
                    "value": correct_answer_text,
                    "type": "text",
                    "original_latex": None
                })

        # Construct the result
        result = {
            "question": question_segments,
            "correctAnswer": correct_answer_segments
        }

        # Return as JSON string
        return json.dumps(result, ensure_ascii=False, indent=2)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format: {str(e)}")
        return json.dumps({"error": f"Invalid JSON format: {str(e)}"}, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Parsing error: {str(e)}")
        return json.dumps({"error": f"Parsing error: {str(e)}"}, ensure_ascii=False, indent=2)

# Example usage (for testing)
if __name__ == "__main__":
    test_json = {
        "question": r"We are tasked with solving a system of linear equations to find the values of $x$ and $y$. This problem involves basic algebraic techniques suitable for beginners, but it will also introduce a variety of mathematical expressions to enrich the context. Consider the following system of equations as the core of our problem:\n\n\\begin{align}\n2x + 3y &= 11, \\\\\n4x - y &= 5.\n\\end{align}\nAdditionally, to provide a broader perspective, imagine that these equations represent constraints in a real-world scenario, such as balancing resources. For instance, let’s suppose $x$ represents the number of units of one item, and $y$ represents another, with costs or quantities constrained by the equations above. As an aside, note that the determinant of the coefficient matrix for this system, given by\n\\begin{vmatrix}\n2 & 3 \\\\\n4 & -1\n\\end{vmatrix} = 2(-1) - 3(4) = -2 - 12 = -14,\nis non-zero, confirming that a unique solution exists.\n\nIn a second layer of exploration, let’s consider a related expression that might arise in a similar context, such as calculating a weighted average or a rate. Suppose we have a secondary expression involving fractions and exponents, like $\\frac{x^2 + y}{3} + 2^{y}$, though this is not directly needed to solve for $x$ and $y$. Furthermore, for conceptual understanding, imagine integrating a simple function related to one of the variables, such as $\\int y \\, dy = \\frac{y^2}{2} + C$, to represent a cumulative effect over time (though again, this is purely for illustration and not required for the solution). Your task remains to solve the original system of equations using substitution or elimination. Provide the values of $x$ and $y$ that satisfy both equations simultaneously.",
        "correctAnswer": "$x=2,y=3$"
    }
    result = parse_json_content(test_json)
    logger.info(result)