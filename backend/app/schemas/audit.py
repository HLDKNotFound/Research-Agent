import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from app.schemas.common import BaseDTO


class AuditLogCreateDTO(BaseDTO):
    user_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    action: str
    resource_type: str
    resource_id: str
    payload: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None


class AuditLogResponseDTO(BaseDTO):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    action: str
    resource_type: str
    resource_id: str
    payload: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime
