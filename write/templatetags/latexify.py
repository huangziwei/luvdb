import re

from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def latexify(context, value):
    # Pattern to detect LaTeX syntax
    LATEX_PATTERN = r"(\$\$?.+?\$\$?|\[.+?\]|\\\(.*?\\\))"

    # Check if content contains LaTeX syntax
    if re.search(LATEX_PATTERN, value):
        # Set flag to include MathJax script in the template
        context["include_mathjax"] = True

    # Return the original content
    return value
