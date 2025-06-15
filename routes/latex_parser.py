import json
import re

def parse_mixed_content_with_original(content):
    """
    Parse a string into an array of text and LaTeX segments, preserving original LaTeX for comparison.
    Args:
        content (str): The input string containing mixed text and LaTeX.
    Returns:
        list: Array of objects with {value: string, type: "text" | "latex", original_latex: string | null}.
              - 'value' is the processed content (for $...$ with math expressions, delimiters removed; 
                for \\(...\\) and \\begin{...}, full original; others as text).
              - 'type' is "text" or "latex".
              - 'original_latex' is the original LaTeX string (including delimiters) for latex type, null for text.
    """
    if not content or not isinstance(content, str):
        return [{"value": "", "type": "text", "original_latex": None}]
    
    result = []
    current_pos = 0
    i = 0
    
    while i < len(content):
        # Check for $...$ (inline math, only if it contains a math expression)
        if content[i] == '$' and i + 1 < len(content) and content[i + 1] != '$':
            if current_pos < i:
                result.append({"value": content[current_pos:i].strip(), "type": "text", "original_latex": None})
            start = i
            i += 1
            while i < len(content) and content[i] != '$':
                i += 1
            if i < len(content) and content[i] == '$' and (i == len(content) - 1 or content[i + 1] != '$'):
                original_latex = content[start:i + 1].strip()
                inner_content = original_latex[1:-1].strip()
                # Only parse as LaTeX if it contains a variable or operator, not just a number
                if re.search(r'[a-zA-Z][^a-zA-Z]*[+\-*/=]|[\\][a-z]+', inner_content) and not re.match(r'^\d+$', inner_content):
                    latex_content = inner_content
                    print(f"Debug: $...$ - original_latex='{original_latex}', latex_content='{latex_content}' (parsed as math)")
                    result.append({"value": latex_content, "type": "latex", "original_latex": original_latex})
                else:
                    print(f"Debug: $...$ - original_latex='{original_latex}' skipped (treated as text)")
                    result.append({"value": original_latex, "type": "text", "original_latex": None})
                current_pos = i + 1
            i += 1
        # Check for $$...$$ (display math)
        elif content[i:i+2] == '$$':
            if current_pos < i:
                result.append({"value": content[current_pos:i].strip(), "type": "text", "original_latex": None})
            start = i
            i += 2
            while i < len(content) and (content[i:i+2] != '$$' or i + 1 >= len(content)):
                i += 1
            if i < len(content) and content[i:i+2] == '$$':
                original_latex = content[start:i + 2].strip()
                latex_content = original_latex[2:-2].strip()  # Remove $$ delimiters
                print(f"Debug: $$...$$ - original_latex='{original_latex}', latex_content='{latex_content}'")
                result.append({"value": latex_content, "type": "latex", "original_latex": original_latex})
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

def parse_json_content(raw_json):
    """
    Parse a JSON object containing 'question' and 'correctAnswer' fields into a structured format.
    Args:
        raw_json (str or dict): The input JSON string or object containing 'question' and 'correctAnswer'.
    Returns:
        str: JSON-formatted string with 'question' and 'correctAnswer' as arrays of {value, type, original_latex} objects.
    """
    try:
        # Ensure raw_json is a dictionary
        if isinstance(raw_json, str):
            json_obj = json.loads(raw_json)
        else:
            json_obj = raw_json

        # Parse question field
        question_segments = parse_mixed_content_with_original(json_obj.get("question", ""))

        # Parse correctAnswer field into an array, treating it as potentially multiple answers
        correct_answer_text = json_obj.get("correctAnswer", "")
        correct_answer_segments = []
        if correct_answer_text:
            # Split by comma if multiple answers are provided (e.g., "$x=24, y=10$")
            answers = [a.strip() for a in correct_answer_text.split(",")]
            for answer in answers:
                if answer:
                    correct_answer_segments.append({
                        "value": answer,
                        "type": "latex",
                        "original_latex": answer  # Preserve original format
                    })

        # Construct the result
        result = {
            "question": question_segments,
            "correctAnswer": correct_answer_segments
        }

        # Return as JSON string
        return json.dumps(result, ensure_ascii=False, indent=2)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON format: {str(e)}"}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Parsing error: {str(e)}"}, ensure_ascii=False, indent=2)

# Example usage (for testing)
if __name__ == "__main__":
    test_json = {
        "question": r"Consider a system of linear equations that models a simple real-world scenario, such as balancing expenses in a budget. Suppose you are managing a small business with two types of products, Product A and Product B. Let $x$ represent the number of units of Product A, and $y$ represent the number of units of Product B. The cost to produce each unit of Product A is $5, and each unit of Product B is $3. Your total budget for production is $150. Additionally, the storage space required for each unit of Product A is $2 square feet, and for Product B, it is $4 square feet, with a total available storage space of $80 square feet. This situation can be modeled by the following system of equations:\n\n\\begin{align*}\n5x + 3y &= 150 \\\\\n2x + 4y &= 80\n\\end{align*}\n\nTo add a layer of complexity, let’s consider a constraint related to the profit margin. Suppose the profit from each unit of Product A is given by the expression $\\frac{3x}{x+1}$, and for Product B, it is $\\frac{2y}{y+2}$. However, for this problem, focus only on solving the system of equations provided above to find the values of $x$ and $y$. As an additional note, ensure that the solution satisfies the practical condition of non-negative values (i.e., $x \\geq 0$ and $y \\geq 0$). Solve this system using any algebraic method, such as substitution or elimination. For extra practice, you may also verify your solution by considering the determinant of the coefficient matrix, given by:\n\n\\begin{vmatrix}\n5 & 3 \\\\\n2 & 4\n\\end{vmatrix}\n\nand ensuring it is non-zero, which guarantees a unique solution. You may also explore a related integral expression for total cost over time, such as $\\int_{0}^{t} (5x + 3y) \, dt$, but this is not required for solving the system.",
        "correctAnswer": "$x=24, y=10$"
    }
    result = parse_json_content(test_json)
    print(result)