import uuid
from typing import AsyncGenerator, Callable, Dict, Optional
from fastapi import Depends, HTTPException, Path, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.core.exceptions import AuthenticationError
from app.core.security import decode_token
from app.models.project import ProjectMember
from app.models.user import User
from app.repositories.user_repository import UserRepository

security = HTTPBearer(auto_error=False)

ROLE_HIERARCHY: Dict[str, int] = {
    "owner": 40,
    "admin": 30,
    "member": 20,
    "viewer": 10,
}


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency yielding a transactional async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Validates JWT Bearer access token:
    - Strictly checks payload['type'] == 'access' (prevents refresh token presentation attacks).
    - Verifies subject UUID.
    - Checks user exists and is active.
    """
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(auth.credentials, expected_type="access")
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise AuthenticationError("Token payload missing subject claim.")
        user_id = uuid.UUID(user_id_str)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    return user


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensures current user is an active superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required.",
        )
    return current_user


def require_project_role(minimum_role: str = "viewer") -> Callable:
    """
    FastAPI dependency factory enforcing Role-Based Access Control on project-scoped endpoints.
    Hierarchy: owner (40) > admin (30) > member (20) > viewer (10).
    Allows global superusers to bypass tenant-level role checks.
    """
    min_weight = ROLE_HIERARCHY.get(minimum_role, 10)

    async def role_checker(
        project_id: uuid.UUID = Path(..., description="Project UUID"),
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db),
    ) -> ProjectMember:
        # Superuser bypass: platform maintainers can access without polluting tenant membership
        if current_user.is_superuser:
            return ProjectMember(project_id=project_id, user_id=current_user.id, role="owner")

        query = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id,
        )
        result = await session.execute(query)
        membership = result.scalars().first()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or you are not a member.",
            )

        user_role_weight = ROLE_HIERARCHY.get(membership.role, 0)
        if user_role_weight < min_weight:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Minimum role required: '{minimum_role}', your role: '{membership.role}'.",
            )

        return membership

    return role_checker
