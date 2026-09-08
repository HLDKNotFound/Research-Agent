import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.cache import cache_service
from app.core.exceptions import AuthenticationError, EntityAlreadyExistsError
from app.core.sanitizer import sanitize_metadata_text, sanitize_email
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    record_active_refresh_token,
    revoke_refresh_token_family,
    rotate_refresh_token_in_redis,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import TokenResponseDTO, UserCreateDTO, UserLoginDTO, UserResponseDTO


class AuthService:
    """Authentication and User Account service with Refresh Token Rotation (RTR) and Family Detection."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def register(self, dto: UserCreateDTO) -> TokenResponseDTO:
        email = sanitize_email(dto.email)
        if await self.user_repo.exists_by_email(email):
            raise EntityAlreadyExistsError("User", "email", email)

        # Sanitize metadata (name) while keeping safe bounds
        clean_name = sanitize_metadata_text(dto.name, max_length=255) if dto.name else None

        user = User(
            email=email,
            password_hash=get_password_hash(dto.password),
            name=clean_name,
            avatar_url=dto.avatar_url,
        )
        created_user = await self.user_repo.create(user)

        access_token = create_access_token(created_user.id)
        refresh_token, jti, family_id = create_refresh_token(created_user.id)

        redis_client = await cache_service.get_client()
        await record_active_refresh_token(redis_client, family_id, jti)

        return TokenResponseDTO(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponseDTO.model_validate(created_user),
        )

    async def login(self, dto: UserLoginDTO) -> TokenResponseDTO:
        email = sanitize_email(dto.email)
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(dto.password, user.password_hash):
            raise AuthenticationError("Invalid email or password.")

        if not user.is_active:
            raise AuthenticationError("User account is deactivated.")

        access_token = create_access_token(user.id)
        refresh_token, jti, family_id = create_refresh_token(user.id)

        redis_client = await cache_service.get_client()
        await record_active_refresh_token(redis_client, family_id, jti)

        return TokenResponseDTO(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponseDTO.model_validate(user),
        )

    async def refresh_token(self, refresh_token_str: str) -> TokenResponseDTO:
        """
        Rotates refresh token (RTR) and issues a new access token.
        Detects reuse/theft: if an already-used refresh token is presented,
        immediately invalidates the entire token family.
        """
        payload = decode_token(refresh_token_str, expected_type="refresh")

        user_id_str = payload.get("sub")
        presented_jti = payload.get("jti")
        family_id = payload.get("family_id")

        if not user_id_str or not presented_jti or not family_id:
            raise AuthenticationError("Malformed refresh token claims.")

        user_id = uuid.UUID(user_id_str)
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or account is deactivated.")

        # Generate new pair in the same token family
        new_access_token = create_access_token(user.id)
        new_refresh_token, new_jti, _ = create_refresh_token(user.id, family_id=family_id)

        # Atomic rotation in Redis with replay detection
        redis_client = await cache_service.get_client()
        await rotate_refresh_token_in_redis(
            redis_client=redis_client,
            family_id=family_id,
            presented_jti=presented_jti,
            new_jti=new_jti,
        )

        return TokenResponseDTO(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            user=UserResponseDTO.model_validate(user),
        )

    async def logout(self, refresh_token_str: str) -> None:
        """Revokes token family upon logout."""
        try:
            payload = decode_token(refresh_token_str, expected_type="refresh")
            family_id = payload.get("family_id")
            if family_id:
                redis_client = await cache_service.get_client()
                await revoke_refresh_token_family(redis_client, family_id)
        except Exception:
            pass  # Silent fail on logout if token is already expired/invalid
