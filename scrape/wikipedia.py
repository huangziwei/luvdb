import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup


def scrape_creator(url):
    language = extract_language_from_url(url)
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    infobox = find_infobox(soup, language)

    if not infobox:
        return None

    data = {
        "name": extract_name(infobox, language),
        "other_names": extract_other_names(infobox, language),
        "creator_type": extract_creator_type(infobox, get_date_label(language, "born")),
        "birth_date": extract_date(infobox, get_date_label(language, "born")),
        "birth_place": extract_place(infobox, get_date_label(language, "born")),
        "death_date": extract_date(infobox, get_date_label(language, "died")),
        "death_place": extract_place(infobox, get_date_label(language, "died")),
        "website": extract_website(infobox),
        "wikipedia": url,
    }

    return data


def scrape_company(url):
    language = extract_language_from_url(url)
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    infobox = soup.find("table", {"class": re.compile("infobox")})

    if not infobox:
        return None

    data = {
        "name": extract_name(infobox, language),
        "founded_date": extract_date(infobox, "Founded"),
        "defunct_date": extract_date(infobox, "Defunct"),
        "location": extract_place(infobox, "Location"),
        "website": extract_website(infobox),
        "wikipedia": url,
    }

    return data


def extract_language_from_url(url):
    match = re.search(r"https?://([a-z]{2,3})\.wikipedia\.org", url)
    return match.group(1) if match else "en"


def find_infobox(soup, language):
    return soup.find("table", {"class": re.compile("infobox")})


def extract_name(infobox, language):
    name_element = infobox.find("th").find(class_="fn")

    if not name_element:
        name_element = infobox.find("th")
    return name_element.get_text(strip=True) if name_element else None


def extract_other_names(infobox, language):
    other_names_element = infobox.find(
        "th", text=re.compile("Other names|Alias|Also known as")
    )
    if other_names_element:
        other_names_element = other_names_element.find_next_sibling("td")
        return other_names_element.get_text(strip=True) if other_names_element else None
    return None


def extract_creator_type(infobox, label):
    # Basic check for person or group based on common fields
    if infobox.find(text=re.compile(label)):
        return "person"
    elif infobox.find(text=re.compile("Origin")):
        return "group"
    return "unknown"


def extract_date(infobox, label):
    date_info = infobox.find("th", text=re.compile(label))
    if date_info:
        date_info = date_info.find_next_sibling("td")
        if date_info:
            # Updated regex to include standalone year format
            date_matches = re.search(
                r"\b(\d{1,2}\s+\w+\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{4})\b",
                date_info.get_text(),
            )
            return format_date(date_matches.group(1)) if date_matches else None
    return None


def extract_place(infobox, label):
    place_info = infobox.find("th", text=re.compile(label))
    if place_info:
        place_info = place_info.find_next_sibling("td")
        if place_info:
            # Remove any <span> and <sup> tags and their contents
            for tag in place_info.find_all(["span", "sup"]):
                tag.decompose()

            # Extracting text after <br> tag
            br_tag = place_info.find("br")
            if br_tag:
                # Collect text from subsequent siblings, which usually contain the place
                place_parts = []
                for sibling in br_tag.next_siblings:
                    if sibling.name and sibling.name != "br":
                        break
                    if sibling.string:
                        place_parts.append(sibling.string.strip())

                return "".join(place_parts).strip()

            # If no <br> tag is found, return the entire text
            return place_info.get_text(strip=True)
    return None


def get_date_label(language, type):
    date_labels = {
        "born": {"en": "Born", "de": "Geboren", "fr": "Né", "zh": "出生", "ja": "生誕"},
        "died": {
            "en": "Died",
            "de": "Gestorben",
            "fr": "Décédé",
            "zh": "逝世",
            "ja": "死没",
        },
    }
    return date_labels[type].get(language, type.capitalize())


def extract_website(infobox):
    website_link = infobox.find("a", {"class": "external text"})
    return website_link.get("href") if website_link else None


def format_date(date_str):
    # Define possible date formats and their corresponding expected output formats
    date_formats = ["%Y-%m-%d", "%Y-%m", "%Y", "%d %B %Y"]
    expected_date_format = ["%Y.%m.%d", "%Y.%m", "%Y", "%Y.%m.%d"]

    for i, fmt in enumerate(date_formats):
        try:
            # Try to parse the date
            return datetime.strptime(date_str, fmt).strftime(expected_date_format[i])
        except ValueError:
            # If parsing fails, try the next format
            continue

    # If all parsing attempts fail, return the original string
    return date_str
