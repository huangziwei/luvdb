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
        inbox = "https://" + message["cc"].split("/")[2] + "/inbox"
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
            "\n",
            response.text,
            "\n",
            header,
            "\n",
            signature,
            "\n",
            target_domain,
            "\n",
            response.status_code,
            "\n",
            response.reason,
            "\n",
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
        print("no signature header")
        return False

    try:
        # Extracting the signature from the header
        signature_header_parts = signature_header.split('signature="')
        if len(signature_header_parts) < 2:
            raise ValueError("Invalid Signature header format.")

        signature_encoded = signature_header_parts[1].rstrip('"')
        signature = base64.b64decode(signature_encoded)
        # print("signature:", signature_encoded)
        # Preparing the signed data
        headers = {
            "(request-target)": f"{request.method.lower()} {request.path}",
            "host": request.get_host(),
            "date": request.headers.get("Date"),
            "digest": request.headers.get("Digest"),
            "content-type": request.headers.get("Content-Type"),
        }
        signed_data = "\n".join(
            f"{k}: {v}" for k, v in headers.items() if v is not None
        )
        # print("signed data:", signed_data)
        # Verifying the signature

        public_key.verify(
            signature, signed_data.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256()
        )
        print("valid signature")
        return True
    except InvalidSignature:
        print("invalid signature")
        return False
    except Exception as e:
        print("Error during signature verification:", str(e))
        return False
