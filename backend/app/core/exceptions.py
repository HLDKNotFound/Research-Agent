from typing import Any, Optional


class DomainException(Exception):
    """Base class for all business domain exceptions."""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.details = details


class EntityNotFoundError(DomainException):
    """Raised when an entity is not found by ID or query criteria."""
    def __init__(self, entity_name: str, entity_id: Any):
        super().__init__(
            message=f"{entity_name} with identifier '{entity_id}' was not found.",
            details={"entity": entity_name, "id": str(entity_id)},
        )


class EntityAlreadyExistsError(DomainException):
    """Raised when attempting to create an entity that already exists."""
    def __init__(self, entity_name: str, key: str, value: Any):
        super().__init__(
            message=f"{entity_name} with {key}='{value}' already exists.",
            details={"entity": entity_name, "key": key, "value": str(value)},
        )


class IdempotencyConflictError(DomainException):
    """Raised when an operation with an idempotency key is already in progress or completed differently."""
    def __init__(self, idempotency_key: str, message: str = "Idempotent operation conflict"):
        super().__init__(
            message=f"{message}: key '{idempotency_key}'",
            details={"idempotency_key": idempotency_key},
        )


class PermissionDeniedError(DomainException):
    """Raised when a user attempts an unauthorized operation on a resource."""
    def __init__(self, message: str = "Permission denied for this resource"):
        super().__init__(message)


class AuthenticationError(DomainException):
    """Raised when user credentials or token validation fails."""
    def __init__(self, message: str = "Invalid authentication credentials"):
        super().__init__(message)


class InvalidStateTransitionError(DomainException):
    """Raised when an entity attempts an illegal state transition (e.g. run queued -> reviewing)."""
    def __init__(self, entity_name: str, current_state: str, target_state: str):
        super().__init__(
            message=f"Cannot transition {entity_name} from '{current_state}' to '{target_state}'.",
            details={"entity": entity_name, "current_state": current_state, "target_state": target_state},
        )
