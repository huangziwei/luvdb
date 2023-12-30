import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


def verify_webmention(source, target):
    """
    Verify the WebMention by ensuring the source page links to the target.
    """
    try:
        response = requests.get(source)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Check if the source page contains a link to the target URL
        for link in soup.find_all("a", href=True):
            if re.match(target, link["href"]):
                return True
        return False
    except requests.RequestException:
        return False


def is_valid_url(url):
    """
    Validate the URL by ensuring it is a valid URL and not blacklisted.
    """
    BLACKLISTED_URLS = []
    # # Check if the URL is blacklisted
    if url in BLACKLISTED_URLS:
        return False

    # Check if the URL is valid
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def fetch_webmention_data(source_url):
    try:
        response = requests.get(source_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Distinguish between h-card and h-entry
        h_card = soup.select_one(".h-card")
        h_entry = soup.select_one(".h-entry")

        # Extract h-card data (author information)
        author_name, author_url, author_handle = None, None, None
        if h_card:
            author_name_el = h_card.select_one(".p-name")
            author_name = (
                author_name_el.get_text(strip=True) if author_name_el else None
            )

            author_url_el = h_card.select_one(".u-url")
            author_url = author_url_el["href"] if author_url_el else None

            if author_url:
                match = re.search(r"https://(.+)/@(.+)", author_url)
                author_handle = f"@{match.group(2)}@{match.group(1)}" if match else None

        # Extract h-entry data (content information)
        content, content_title, content_url = None, None, None
        if h_entry:
            content_el = h_entry.select_one(".e-content")
            content = content_el.get_text() if content_el else None

            content_title_el = h_entry.select_one(".p-name")
            content_title = content_title_el.get_text() if content_title_el else None

            content_url_el = h_entry.select_one(".u-url")
            content_url = content_url_el["href"] if content_url_el else None

        # Determine the type of WebMention
        mention_type = "other"
        if "/post/" in source_url:
            mention_type = "post"
        elif "/repost/" in source_url:
            mention_type = "repost"
        elif "/comment/" in source_url or (
            h_entry and h_entry.select_one(".e-content")
        ):
            mention_type = "comment"

        # Organize data
        data = {
            "author_name": author_name,
            "author_url": author_url,
            "author_handle": author_handle,
            "content": content,
            "content_title": content_title,
            "content_url": content_url,
            "mention_type": mention_type,
        }

        return data
    except requests.RequestException:
        # Handle exceptions
        return {}


def discover_webmention_endpoint(target_url):
    """
    Discover if a target URL supports WebMentions and return the endpoint.
    """
    try:
        response = requests.get(target_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        link_tag = soup.find("link", rel="webmention")
        if link_tag:
            return link_tag["href"]
        return None
    except requests.RequestException:
        return None


def find_all_webmention_targets(content):
    """
    Find the all links in the content that is a valid URL and not blacklisted.
    """
    # Find all links in the content
    links = re.findall(r"<a[^>]+href=\"(.*?)\"", content)
    # Filter out invalid URLs
    links = filter(is_valid_url, links)
    return list(links)
