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


def create_bluesky_post(handle: str, password: str, text: str, say_id: int):
    session = bsky_login_session(handle, password)
    pds_url = "https://bsky.social"
    access_token = session.get("accessJwt")
    user_did = session.get("did")

    if not all([access_token, pds_url, user_did]):
        raise ValueError("Invalid session data")

    # Create the link back to your site
    domain = settings.ROOT_URL  # Using domain from settings
    say_url = domain + reverse("write:say_detail", args=[say_id])
    truncated_text = text[: 300 - len(say_url) - 1]  # Adjust for space and URL length
    post_content = f"{truncated_text} {say_url}"

    # Prepare the post data
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    post_data = {
        "$type": "app.bsky.feed.post",
        "text": post_content,
        "createdAt": now,
    }

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
