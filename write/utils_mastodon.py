from django.conf import settings
from django.urls import reverse
from mastodon import Mastodon


def create_mastodon_post(handle, access_token, text, url):
    # Initialize Mastodon
    instance_url = f"https://{handle.split('@')[1]}"
    mastodon = Mastodon(access_token=access_token, api_base_url=instance_url)

    # Create the post content
    max_length = 500 - len(url) - 4  # Account for newline and ellipsis
    if len(text) > max_length:
        text = text[:max_length] + "…"
    post_content = f"{text}\n\n{url}"

    # Post the update
    return mastodon.status_post(status=post_content)


# def create_mastodon_post(
#     handle: str,
#     access_token: str,
#     text: str,
#     content_id: int,
#     content_username: str,
#     content_type: str,
# ):
#     # Extract instance URL from handle
#     instance_url = f"https://{handle.split('@')[1]}"

#     # Initialize Mastodon
#     mastodon = Mastodon(access_token=access_token, api_base_url=instance_url)

#     # Create the link back to your site
#     domain = settings.ROOT_URL  # Using domain from settings
#     if content_type == "Say":
#         content_url = domain + reverse(
#             "write:say_detail", kwargs={"pk": content_id, "username": content_username}
#         )
#     elif content_type == "Post":
#         content_url = domain + reverse(
#             "write:post_detail",
#             kwargs={"pk": content_id, "username": content_username},
#         )
#     elif content_type == "Pin":
#         content_url = domain + reverse(
#             "write:pin_detail", kwargs={"pk": content_id, "username": content_username}
#         )
#     elif content_type == "Repost":
#         content_url = domain + reverse(
#             "write:repost_detail",
#             kwargs={"pk": content_id, "username": content_username},
#         )
#     elif content_type == "ReadCheckIn":
#         content_url = domain + reverse(
#             "write:read_checkin_detail",
#             kwargs={"pk": content_id, "username": content_username},
#         )
#     elif content_type == "WatchCheckIn":
#         content_url = domain + reverse(
#             "write:watch_checkin_detail",
#             kwargs={"pk": content_id, "username": content_username},
#         )
#     elif content_type == "ListenCheckIn":
#         content_url = domain + reverse(
#             "write:listen_checkin_detail",
#             kwargs={"pk": content_id, "username": content_username},
#         )
#     elif content_type == "PlayCheckIn":
#         content_url = domain + reverse(
#             "write:play_checkin_detail",
#             kwargs={"pk": content_id, "username": content_username},
#         )
#     elif content_type == "VisitCheckIn":
#         content_url = domain + reverse(
#             "write:visit_checkin_detail",
#             kwargs={"pk": content_id, "username": content_username},
#         )
#     else:
#         content_url = ""

#     # Determine if text needs to be truncated
#     max_length = (
#         500 - len(content_url) - 4
#     )  # 4 for newline characters and potential ellipsis
#     if len(text) > max_length:
#         truncated_text = text[:max_length] + "…"
#     else:
#         truncated_text = text

#     post_content = f"{truncated_text}\n\n{content_url}"

#     # Post the update
#     return mastodon.status_post(status=post_content)
