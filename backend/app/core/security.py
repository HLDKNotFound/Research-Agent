import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Tuple, Union
import bcrypt
import jwt
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.exceptions import AuthenticationError


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against its bcrypt hash, respecting the 72-byte limit."""
    try:
        pwd_bytes = plain_password.encode("utf-8")
        if len(pwd_bytes) > settings.BCRYPT_MAX_PASSWORD_BYTES:
            return False
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """
    Generates a secure bcrypt hash for a password.
    Enforces maximum password length (72 bytes) to prevent Denial of Service via computationally expensive hashing.
    """
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) > settings.BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password cannot be longer than {settings.BCRYPT_MAX_PASSWORD_BYTES} bytes."
        )
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    """Creates a signed JWT access token with explicit type='access' claim and unique jti."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "access",
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: Union[str, Any],
    family_id: Optional[str] = None,
) -> Tuple[str, str, str]:
    """
    Creates a signed JWT refresh token with unique jti and family_id for Token Rotation (RTR).
    Returns (token_str, jti, family_id).
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    token_family = family_id or str(uuid.uuid4())

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "refresh",
        "jti": jti,
        "family_id": token_family,
    }
    token_str = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token_str, jti, token_family


def decode_token(token: str, expected_type: Optional[str] = None) -> dict[str, Any]:
    """
    Decodes and validates a JWT token, strictly verifying token type claim if specified.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired.")
    except jwt.PyJWTError as e:
        raise AuthenticationError(f"Invalid token: {e}")

    if expected_type:
        actual_type = payload.get("type")
        if actual_type != expected_type:
            raise AuthenticationError(
                f"Invalid token type: expected '{expected_type}', got '{actual_type}'."
            )

    return payload


# --- Redis-based Refresh Token Rotation (RTR) & Family Detection ---

FAMILY_ACTIVE_PREFIX = "v1:auth:family:active:"
FAMILY_REVOKED_PREFIX = "v1:auth:family:revoked:"
REFRESH_TTL = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400


async def record_active_refresh_token(
    redis_client: Optional[aioredis.Redis],
    family_id: str,
    jti: str,
) -> None:
    """Records the currently active jti for a token family."""
    if redis_client is None:
        return
    key = f"{FAMILY_ACTIVE_PREFIX}{family_id}"
    await redis_client.set(key, jti, ex=REFRESH_TTL)


async def rotate_refresh_token_in_redis(
    redis_client: Optional[aioredis.Redis],
    family_id: str,
    presented_jti: str,
    new_jti: str,
) -> None:
    """
    Implements Refresh Token Rotation with reuse detection.
    If the presented jti does not match the active jti (meaning an already-used token was replayed),
    revokes the entire family immediately to protect against token compromise.
    """
    if redis_client is None:
        return

    # Check if family is already revoked
    revoked_key = f"{FAMILY_REVOKED_PREFIX}{family_id}"
    if await redis_client.get(revoked_key):
        raise AuthenticationError(
            "Compromised refresh token family. All associated sessions have been revoked."
        )

    active_key = f"{FAMILY_ACTIVE_PREFIX}{family_id}"
    current_active_jti = await redis_client.get(active_key)

    if current_active_jti is not None and current_active_jti != presented_jti:
        # Replay / Reuse attack detected!
        # An old refresh token was used again -> revoke the entire family!
        await redis_client.set(revoked_key, "1", ex=REFRESH_TTL)
        await redis_client.delete(active_key)
        raise AuthenticationError(
            "Refresh token reuse detected (possible theft). All sessions in this token family have been terminated."
        )

    # Valid rotation: set new active jti
    await redis_client.set(active_key, new_jti, ex=REFRESH_TTL)


async def revoke_refresh_token_family(
    redis_client: Optional[aioredis.Redis],
    family_id: str,
) -> None:
    """Revokes an entire refresh token family."""
    if redis_client is None:
        return
    revoked_key = f"{FAMILY_REVOKED_PREFIX}{family_id}"
    active_key = f"{FAMILY_ACTIVE_PREFIX}{family_id}"
    await redis_client.set(revoked_key, "1", ex=REFRESH_TTL)
    await redis_client.delete(active_key)
