"""JWT authentication helpers."""
import hmac
import hashlib
import base64
import json
import os
import time

SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not SECRET_KEY:
    import warnings
    warnings.warn(
        "JWT_SECRET_KEY not set — using insecure default for development only. "
        "Set JWT_SECRET_KEY env var in production.",
        UserWarning,
        stacklevel=2,
    )
    SECRET_KEY = "insecure-dev-secret-do-not-use-in-production"
TOKEN_TTL_SECONDS = 60 * 60 * 24 * 365  # 1 year


def _base64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _base64_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def encode_token(user_id: str, expires_at: int | None = None) -> str:
    """Create a JWT-like token."""
    if expires_at is None:
        expires_at = int(time.time()) + TOKEN_TTL_SECONDS

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": user_id, "exp": expires_at}

    header_b64 = _base64_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _base64_encode(json.dumps(payload, separators=(",", ":")).encode())

    signature = hmac.new(
        SECRET_KEY.encode(),
        f"{header_b64}.{payload_b64}".encode(),
        hashlib.sha256,
    ).digest()
    sig_b64 = _base64_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_token(token: str) -> str | None:
    """Decode and validate a token. Returns user_id if valid, None otherwise."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, sig_b64 = parts

        expected_sig = hmac.new(
            SECRET_KEY.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256,
        ).digest()
        expected_sig_b64 = _base64_encode(expected_sig)

        if not hmac.compare_digest(sig_b64, expected_sig_b64):
            return None

        payload_bytes = _base64_decode(payload_b64)
        payload = json.loads(payload_bytes)

        if payload.get("exp", 0) < int(time.time()):
            return None

        return payload.get("sub")
    except Exception:
        return None
