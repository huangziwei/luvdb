import base64
import json
import uuid
from datetime import datetime

import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings
from environs import Env

User = settings.AUTH_USER_MODEL


def import_private_key(username):
    env = Env()
    env.read_env(settings.PRIVATEKEY_PATH)

    # Access and decode the key
    encoded_private_key = env.str(username)

    private_key = serialization.load_pem_private_key(
        base64.b64decode(encoded_private_key),
        password=None,
    )
    return private_key


def digest_message(message):
    HASH = hashes.SHA256()
    digest = hashes.Hash(HASH)
    digest.update(message.encode("utf-8"))
    return base64.b64encode(digest.finalize())


def sign_and_send(message, name, domain, target_domain, private_key):
    HASH = hashes.SHA256()

    if "cc" in message:
        inbox = "https://" + message["cc"][0].split("/")[2] + "/inbox"
    else:
        inbox = message["object"]["actor"] + "/inbox"
    inbox_fragment = inbox.replace(f"https://{target_domain}", "")
    digest_hash = digest_message(json.dumps(message))

    d = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    string_to_sign = f"(request-target): post {inbox_fragment}\nhost: {target_domain}\ndate: {d}\ndigest: SHA-256={digest_hash.decode('utf-8')}"
    signature = base64.b64encode(
        private_key.sign(string_to_sign.encode("utf-8"), padding.PKCS1v15(), HASH)
    ).decode("utf-8")

    header = f'keyId="{domain}{name}",headers="(request-target) host date digest",signature="{signature}"'
    response = requests.post(
        inbox,
        headers={
            "Host": target_domain,
            "Date": d,
            "Digest": f'SHA-256={digest_hash.decode("utf-8")}',
            "Content-Type": "application/json",
            "Signature": header,
        },
        data=json.dumps(message),
    )

    if response.status_code >= 400:
        print(
            "Failed request",
            response.status_code,
            "\n",
            response.text,
            "\n",
            header,
            "\n",
            target_domain,
            "\n",
            inbox,
        )
        return False
    else:
        print("Response:", "\n", response.text, "\n", header, "\n")
        return True


def verify_requests(request, public_key):
    """
    Verify the signature of the request using the public key of the sender.
    """
    signature_header = request.headers.get("Signature")
    if not signature_header:
        return False

    try:
        # Parsing the signature header
        parts = {}
        for part in signature_header.split(","):
            if "=" in part:
                key, _, value = part.partition("=")
                parts[key.strip()] = value.strip().strip('"')

        # Decode the signature
        signature_encoded = parts["signature"]
        signature = base64.b64decode(signature_encoded)

        # Extract and order the headers as per the 'headers' component
        headers_to_sign = parts.get("headers").split()
        signed_data = "\n".join(
            f"{header}: {request.headers.get(header.capitalize(), '')}"
            if header != "(request-target)"
            else f"(request-target): {request.method.lower()} {request.path}"
            for header in headers_to_sign
        )

        # Verifying the signature
        public_key.verify(
            signature, signed_data.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256()
        )
        return True
    except InvalidSignature:
        return False
    except Exception as e:
        return False
