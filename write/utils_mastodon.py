from django.conf import settings
from django.urls import reverse
from mastodon import Mastodon


def create_mastodon_post(
    handle: str, access_token: str, text: str, content_id: int, content_type: str
):
    # Extract instance URL from handle
    instance_url = f"https://{handle.split('@')[1]}"

    # Initialize Mastodon
    mastodon = Mastodon(access_token=access_token, api_base_url=instance_url)

    # Create the link back to your site
    domain = settings.ROOT_URL  # Using domain from settings
    if content_type == "Say":
        content_url = domain + reverse("write:say_detail", args=[content_id])
    elif content_type == "Post":
        content_url = domain + reverse("write:post_detail", args=[content_id])
    elif content_type == "Pin":
        content_url = domain + reverse("write:pin_detail", args=[content_id])
    elif content_type == "Repost":
        content_url = domain + reverse("write:repost_detail", args=[content_id])
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
    else:
        content_url = ""

    # Determine if text needs to be truncated
    max_length = (
        500 - len(content_url) - 4
    )  # 4 for newline characters and potential ellipsis
    if len(text) > max_length:
        truncated_text = text[:max_length] + "..."
    else:
        truncated_text = text

    post_content = f"{truncated_text}\n\n{content_url}"

    # Post the update
    return mastodon.status_post(status=post_content)
