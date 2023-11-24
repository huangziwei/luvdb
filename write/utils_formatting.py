import re


def needs_mathjax(value):
    MATHJAX_FLAG_PATTERN = r"```math\s*(.*?)\s*```"
    return re.search(MATHJAX_FLAG_PATTERN, value) is not None


def needs_mermaid(value):
    MERMAID_MD_PATTERN = r"```mermaid\s*(.*?)\s*```"
    return re.search(MERMAID_MD_PATTERN, value, re.DOTALL | re.IGNORECASE) is not None


def check_required_js(objects):
    # Initialize flags
    include_mathjax = False
    include_mermaid = False

    # Check each activity item for both MathJax and Mermaid requirements
    for obj in objects:
        try:
            content = obj.content
        except:
            try:
                content = obj.content_object.content
            except:
                continue
        try:
            if obj.model_name == "Repost":
                content += obj.original_activity.content_object.content
        except:
            pass

        if not include_mathjax and needs_mathjax(content):
            include_mathjax = True
        if not include_mermaid and needs_mermaid(content):
            include_mermaid = True

        # Break the loop if both flags are set
        if include_mathjax and include_mermaid:
            break

    return include_mathjax, include_mermaid
