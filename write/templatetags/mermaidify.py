import re

from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def mermaidify(context, value):
    # Pattern to detect Mermaid blocks in Markdown
    MERMAID_MD_PATTERN = r"```mermaid\s*(.*?)\s*```"

    # Function to replace Mermaid block with HTML div
    def replace_with_div(match):
        # Set flag to include Mermaid script in the template
        context["include_mermaid"] = True
        return '<div class="mermaid">{}</div>'.format(match.group(1))

    # Replace Mermaid Markdown blocks with HTML divs
    processed_value = re.sub(
        MERMAID_MD_PATTERN, replace_with_div, value, flags=re.DOTALL | re.IGNORECASE
    )

    return processed_value
