import re


def needs_mathjax(value):
    MATHJAX_FLAG_PATTERN = r"<!--\s*mathjax\s*-->"
    return re.search(MATHJAX_FLAG_PATTERN, value) is not None


def needs_mermaid(value):
    MERMAID_MD_PATTERN = r"```mermaid\s*(.*?)\s*```"
    return re.search(MERMAID_MD_PATTERN, value, re.DOTALL | re.IGNORECASE) is not None
