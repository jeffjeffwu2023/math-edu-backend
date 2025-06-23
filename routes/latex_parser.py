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
    Parse a string into an array of text and LaTeX segments, using custom markers as delimiters.
    If the content starts with '_FLG_LATEX_INLINE_START_' and ends with '_FLG_LATEX_INLINE_END_',
    replace them with '\(' and '\)' respectively before segmentation.
    Args:
        content (str): The input string containing mixed text and LaTeX with custom markers.
    Returns:
        list: Array of objects with {value: string, type: "text" | "latex", original_latex: string | None}.
              - 'value' is the processed content with restored LaTeX within markers, wrapped in \( \) for LaTeX segments.
              - 'type' is "text" or "latex" based on marker presence.
              - 'original_latex' is the original marked-up string for reference.
    """
    if not content or not isinstance(content, str):
        return [{"value": "", "type": "text", "original_latex": None}]
    
    logger.info(f"Debug: Starting parse_mixed_content_with_original with content length {len(content)}")
    logger.info(f"Debug: Initial content: {content}")

    # Preprocess: Check if content is fully enclosed by _FLG_LATEX_INLINE_START_ and _FLG_LATEX_INLINE_END_
    if (content.startswith('_FLG_LATEX_INLINE_START_') and 
        content.endswith('_FLG_LATEX_INLINE_END_')):
        content = '\\(' + content[len('_FLG_LATEX_INLINE_START_'):-len('_FLG_LATEX_INLINE_END_')] + '\\)'
        logger.info(f"Debug: Replaced _FLG_LATEX_INLINE_START_ and _FLG_LATEX_INLINE_END_ with \\( and \\), new content: {content}")

    result = []
    current_pos = 0
    i = 0
    
    while i < len(content):
        # Check for _FLG_LATEX_INLINE_START_ (inline LaTeX)
        if content.startswith('_FLG_LATEX_INLINE_START_', i):
            if current_pos < i:
                result.append({"value": content[current_pos:i].strip(), "type": "text", "original_latex": content[current_pos:i].strip()})
            start = i
            i += len('_FLG_LATEX_INLINE_START_')
            logger.info(f"Debug: Found _FLG_LATEX_INLINE_START_ at position {start}")
            while i < len(content) and not content.startswith('_FLG_LATEX_INLINE_END_', i):
                i += 1
            if i < len(content) and content.startswith('_FLG_LATEX_INLINE_END_', i):
                logger.info(f"Debug: Found _FLG_LATEX_INLINE_END_ at position {i}")
                original_latex = content[start:i + len('_FLG_LATEX_INLINE_END_')]
                inner_content = content[start + len('_FLG_LATEX_INLINE_START_'):i]
                result.append({"value": '\\(' + inner_content + '\\)', "type": "latex", "original_latex": original_latex})
                current_pos = i + len('_FLG_LATEX_INLINE_END_')
                i += len('_FLG_LATEX_INLINE_END_')
            else:
                logger.warning(f"Unmatched _FLG_LATEX_INLINE_START_ at position {start}, treating remainder as text")
                result.append({"value": content[current_pos:].strip(), "type": "text", "original_latex": content[current_pos:].strip()})
                break
                
        # Check for _FLG_LATEX_CENTER_START_ (centered block LaTeX)
        elif content.startswith('_FLG_LATEX_CENTER_START_', i):
            if current_pos < i:
                result.append({"value": content[current_pos:i].strip(), "type": "text", "original_latex": content[current_pos:i].strip()})
            start = i
            i += len('_FLG_LATEX_CENTER_START_')
            logger.info(f"Debug: Found _FLG_LATEX_CENTER_START_ at position {start}")
            while i < len(content) and not content.startswith('_FLG_LATEX_CENTER_END_', i):
                i += 1
            if i < len(content) and content.startswith('_FLG_LATEX_CENTER_END_', i):
                logger.info(f"Debug: Found _FLG_LATEX_CENTER_END_ at position {i}")
                original_latex = content[start:i + len('_FLG_LATEX_CENTER_END_')]
                inner_content = content[start + len('_FLG_LATEX_CENTER_START_'):i]
                result.append({"value": '\\(' + inner_content + '\\)', "type": "latex", "original_latex": original_latex})
                current_pos = i + len('_FLG_LATEX_CENTER_END_')
                i += len('_FLG_LATEX_CENTER_END_')
            else:
                logger.warning(f"Unmatched _FLG_LATEX_CENTER_START_ at position {start}, treating remainder as text")
                result.append({"value": content[current_pos:].strip(), "type": "text", "original_latex": content[current_pos:].strip()})
                break
        
        # Check for other text
        else:
            i += 1
    
    if current_pos < len(content):
        result.append({"value": content[current_pos:].strip(), "type": "text", "original_latex": content[current_pos:].strip()})
    
    # Post-process: Replace all _CMD_LATEX_ markers with their original LaTeX values
    for segment in result:
        segment["value"] = segment["value"].replace("_CMD_LATEX_CDOT-", "\\cdot")
        segment["value"] = segment["value"].replace("_CMD_LATEX_INT-", "\\int")
        segment["value"] = segment["value"].replace("_CMD_LATEX_SUM-", "\\sum")
        segment["value"] = re.sub(r'_CMD_LATEX_TEXTBF_START_([^]_CMD_LATEX_TEXTBF_END_]+)_CMD_LATEX_TEXTBF_END_', r'\\textbf{\1}', segment["value"])
        segment["value"] = re.sub(r'_CMD_LATEX_FRACTION_START-([^]_CMD_LATEX_FRACTION_END_]+)_CMD_LATEX_FRACTION_END_([^}-]+)', r'\\frac{\1}{\2}', segment["value"])
        segment["value"] = segment["value"].replace("_BACKSLASH_", "\\")
        segment["value"] = segment["value"].replace("_CMD_LATEX_", "\\")

    # Logger results for debugging
    for idx, segment in enumerate(result):
        logger.info(f"Segment {idx}: value='{segment['value']}', type='{segment['type']}', original_latex='{segment['original_latex']}'")

    return result


# Example usage (for testing)
if __name__ == "__main__":
    # Test Case 1: Content fully enclosed by _FLG_LATEX_INLINE_START_ and _FLG_LATEX_INLINE_END_
    test_content1 = "_FLG_LATEX_INLINE_START_2x + 3y = 11_FLG_LATEX_INLINE_END_"
    result1 = parse_mixed_content_with_original(test_content1)
    logger.info("Test Case 1 Result: %s", result1)

    # Test Case 2: Multiple inline LaTeX segments
    test_content2 = "Text before _FLG_LATEX_INLINE_START_x + y_FLG_LATEX_INLINE_END_ and _FLG_LATEX_INLINE_START_z_FLG_LATEX_INLINE_END_ text after"
    result2 = parse_mixed_content_with_original(test_content2)
    logger.info("Test Case 2 Result: %s", result2)

    # Test Case 3: Centered block LaTeX segment
    test_content3 = "Text before _FLG_LATEX_CENTER_START_2x + 3y = 11_FLG_LATEX_CENTER_END_ text after"
    result3 = parse_mixed_content_with_original(test_content3)
    logger.info("Test Case 3 Result: %s", result3)

    # Test Case 4: Mixed content with unmatched marker
    test_content4 = "Text _FLG_LATEX_INLINE_START_x + y unmatched"
    result4 = parse_mixed_content_with_original(test_content4)
    logger.info("Test Case 4 Result: %s", result4)