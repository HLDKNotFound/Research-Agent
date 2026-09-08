from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseDTO(BaseModel):
    """Base DTO with orm_mode enabled for Pydantic v2."""
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


class PaginatedResponse(BaseDTO, Generic[T]):
    items: List[T]
    total: int
    page: int
    limit: int
    total_pages: int

    @classmethod
    def create(cls, items: List[T], total: int, params: PaginationParams) -> "PaginatedResponse[T]":
        total_pages = (total + params.limit - 1) // params.limit if params.limit > 0 else 1
        return cls(
            items=items,
            total=total,
            page=params.page,
            limit=params.limit,
            total_pages=total_pages,
        )
