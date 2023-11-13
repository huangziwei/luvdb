import re
from datetime import datetime, timezone

import requests
from django.conf import settings
from django.urls import reverse


def bsky_login_session(handle: str, password: str) -> dict:
    pds_url = "https://bsky.social"
    resp = requests.post(
        pds_url + "/xrpc/com.atproto.server.createSession",
        json={"identifier": handle, "password": password},
    )
    resp.raise_for_status()
    return resp.json()


url_regex = re.compile(
    r"[$|\W](https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*[-a-zA-Z0-9@%_\+~#//=])?)"
)


def parse_urls(text: str):
    spans = []
    for m in url_regex.finditer(text):
        spans.append(
            {
                "start": m.start(1),
                "end": m.end(1),
                "url": m.group(1),
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
    handle: str, password: str, text: str, content_id: int, content_type: str
):
    session = bsky_login_session(handle, password)
    pds_url = "https://bsky.social"
    access_token = session.get("accessJwt")
    user_did = session.get("did")

    if not all([access_token, pds_url, user_did]):
        raise ValueError("Invalid session data")

    # Create the link back to your site
    domain = settings.ROOT_URL  # Using domain from settings
    if content_type == "Say":
        content_url = domain + reverse("write:say_detail", args=[content_id])
    elif content_type == "Post":
        content_url = domain + reverse("write:post_detail", args=[content_id])
    elif content_type == "Pin":
        content_url = domain + reverse("write:pin_detail", args=[content_id])
    elif content_type == "ReadCheckIn":
        content_url = domain + reverse("read:read_checkin_detail", args=[content_id])
    elif content_type == "WatchCheckIn":
        content_url = domain + reverse("watch:watch_checkin_detail", args=[content_id])
    elif content_type == "ListenCheckIn":
        content_url = domain + reverse(
            "listen:listen_checkin_detail", args=[content_id]
        )
    elif content_type == "GameCheckIn":
        content_url = domain + reverse("game:game_checkin_detail", args=[content_id])
    truncated_text = text[: 300 - len(content_url) - 1]
    post_content = f"{truncated_text} {content_url}"

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
