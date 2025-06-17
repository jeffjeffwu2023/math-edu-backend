import re

def process_latex_in_text(content):
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

        # Replace starting \
        if inner.startswith('\\'):
            inner = '-BACKSLASH-' + inner[1:]

        # Replace all LaTeX commands: \command{...} or \command
        def cmd_replacer(m):
            cmd = m.group(1)
            arg = m.group(2) if m.group(2) else ""
            return f"-CMD-LATEX-{cmd}{arg}"

        inner = re.sub(r'\\([a-zA-Z]+)(\{[^}]*\})?', cmd_replacer, inner)

        # Replace \end{...} at end
        inner, count = re.subn(
            r'-CMD-LATEX-end(\{[^}]+\})\s*$',
            r'-CMD-LATEX-END-end\1',
            inner
        )

        # If no \end matched, append CMD-LATEX-END
        if count == 0:
            inner += '-CMD-LATEX-END-'

        return prefix + inner

    # Pattern: inline, display, environment
    pattern = r'(\$.*?\$|\\\(.*?\\\)|\\\[.*?\\\]|\\begin\{[^}]*\}.*?\\end\{[^}]*\})'

    result = re.sub(pattern, replacer, content, flags=re.DOTALL)
    return result




if __name__ == "__main__":
    text = (
        'Inline: $\\frac{x}{2} + y$. '
        'Block: \\begin{align} x + y = 1 \\\\ z = 2 \\end{align}.'
    )

    processed = process_latex_in_text(text)
    print("Original:", text)
    print("Processed:", processed)
