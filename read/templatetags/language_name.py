import pycountry
from django import template
from langcodes import Language

register = template.Library()


@register.filter
def language_name(lang_code):
    if lang_code == "zh-Hans":
        return "简体中文"
    elif lang_code == "zh-Hant":
        return "繁體中文"
    try:
        # Attempt to get language from pycountry
        language = pycountry.languages.get(alpha_2=lang_code)
        # Using langcodes to get the autonym
        return Language.make(language.alpha_2).autonym()
    except:
        return lang_code  # return the code if we can't find a name
