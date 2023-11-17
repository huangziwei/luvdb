import re
from datetime import datetime, timezone

import requests
from django.conf import settings
from django.urls import reverse
from mastodon import Mastodon


def bsky_login_session(handle: str, pds_url: str, password: str) -> dict:
    resp = requests.post(
        pds_url + "/xrpc/com.atproto.server.createSession",
        json={"identifier": handle, "password": password},
    )
    resp.raise_for_status()
    return resp.json()


url_regex = re.compile(
    rb"(https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}([-a-zA-Z0-9()@:%_\+.~#?&//=]*))"
)


def parse_urls(text: str):
    spans = []
    byte_text = text.encode("utf-8")
    for m in url_regex.finditer(byte_text):
        spans.append(
            {
                "start": m.start(1),
                "end": m.end(1),
                "url": m.group(1).decode("utf-8"),
            }
        )
    return spans


def create_url_facets(text: str):
    return [
        {
            "index": {
                "byteStart": url_info["start"],
                "byteEnd": url_info["end"],
            },
            "features": [
                {
                    "$type": "app.bsky.richtext.facet#link",
                    "uri": url_info["url"],
                }
            ],
        }
        for url_info in parse_urls(text)
    ]


def create_bluesky_post(
    handle: str,
    pds_url: str,
    password: str,
    text: str,
    content_id: int,
    content_username: str,
    content_type: str,
):
    session = bsky_login_session(handle, pds_url, password)
    access_token = session.get("accessJwt")
    user_did = session.get("did")

    if not all([access_token, pds_url, user_did]):
        raise ValueError("Invalid session data")

    # Create the link back to your site
    domain = settings.ROOT_URL  # Using domain from settings
    if content_type == "Say":
        content_url = domain + reverse(
            "write:say_detail",
            kwargs={"pk": content_id, "username": content_username},
        )
    elif content_type == "Post":
        content_url = domain + reverse(
            "write:post_detail",
            kwargs={"pk": content_id, "username": content_username},
        )
    elif content_type == "Pin":
        content_url = domain + reverse(
            "write:pin_detail", kwargs={"pk": content_id, "username": content_username}
        )
    elif content_type == "Repost":
        content_url = domain + reverse(
            "write:repost_detail",
            kwargs={"pk": content_id, "username": content_username},
        )
    elif content_type == "ReadCheckIn":
        content_url = domain + reverse(
            "write:read_checkin_detail",
            kwargs={"pk": content_id, "username": content_username},
        )
    elif content_type == "WatchCheckIn":
        content_url = domain + reverse(
            "write:watch_checkin_detail",
            kwargs={"pk": content_id, "username": content_username},
        )
    elif content_type == "ListenCheckIn":
        content_url = domain + reverse(
            "write:listen_checkin_detail",
            kwargs={"pk": content_id, "username": content_username},
        )
    elif content_type == "GameCheckIn":
        content_url = domain + reverse(
            "write:play_checkin_detail",
            kwargs={"pk": content_id, "username": content_username},
        )
    else:
        content_url = ""

    # Determine if text needs to be truncated
    max_length = (
        300 - len(content_url) - 3
    )  # 3 for newline characters and potential ellipsis
    if len(text) > max_length:
        truncated_text = text[:max_length] + "…"
    else:
        truncated_text = text

    post_content = f"{truncated_text}\n\n{content_url}"

    # Prepare the post data
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    post_data = {
        "$type": "app.bsky.feed.post",
        "text": post_content,
        "createdAt": now,
    }
    # Parse URLs and create facets
    url_facets = create_url_facets(post_content)
    if url_facets:
        post_data["facets"] = url_facets

    # Send the post request to BlueSky
    response = requests.post(
        pds_url + "/xrpc/com.atproto.repo.createRecord",
        headers={"Authorization": "Bearer " + access_token},
        json={
            "repo": user_did,
            "collection": "app.bsky.feed.post",
            "record": post_data,
        },
    )
    response.raise_for_status()
    return response.json()
