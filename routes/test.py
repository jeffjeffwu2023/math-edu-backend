import re

restored_content = "x"
restored_content = re.sub(r'_CMD_LATEX_TEXTBF_START_([^]_CMD_LATEX_TEXTBF_END_]+)_CMD_LATEX_TEXTBF_END_', r'\\textbf{\1}', restored_content)
print(restored_content)
               