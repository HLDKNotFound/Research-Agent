from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.core.exceptions import AuthenticationError, EntityAlreadyExistsError
from app.core.rate_limiter import check_rate_limit
from app.models.user import User
from app.schemas.user import TokenResponseDTO, UserCreateDTO, UserLoginDTO, UserResponseDTO
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/register", response_model=TokenResponseDTO, status_code=status.HTTP_201_CREATED)
async def register(
    dto: UserCreateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TokenResponseDTO:
    """Register a new user account with rate-limiting against credential stuffing."""
    await check_rate_limit(request, action="auth_register")
    service = AuthService(session)
    try:
        return await service.register(dto)
    except EntityAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)


@router.post("/login", response_model=TokenResponseDTO)
async def login(
    dto: UserLoginDTO,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TokenResponseDTO:
    """Authenticate with email and password, issuing access & refresh tokens."""
    await check_rate_limit(request, action="auth_login")
    service = AuthService(session)
    try:
        return await service.login(dto)
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=TokenResponseDTO)
async def refresh_token(
    dto: RefreshTokenRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TokenResponseDTO:
    """Rotate refresh token (RTR) and issue a new access token. Replay attacks revoke the family."""
    await check_rate_limit(request, action="auth_refresh")
    service = AuthService(session)
    try:
        return await service.refresh_token(dto.refresh_token)
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    dto: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db),
) -> None:
    """Log out and revoke the refresh token family."""
    service = AuthService(session)
    await service.logout(dto.refresh_token)


@router.get("/me", response_model=UserResponseDTO)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponseDTO:
    """Return profile of currently authenticated user."""
    return UserResponseDTO.model_validate(current_user)
