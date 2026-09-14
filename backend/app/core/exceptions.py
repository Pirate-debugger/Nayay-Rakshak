from fastapi import HTTPException, status


class SecurityValidationError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class PromptInjectionDetected(HTTPException):
    def __init__(self, detail: str = "Suspicious prompt injection pattern detected in input"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class FileIntegrityError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=detail)

class ObjectNotFoundError(HTTPException):
    def __init__(self, entity_name: str = "Object"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity_name} not found or access unauthorized")

class UnauthorizedAccessError(HTTPException):
    def __init__(self, detail: str = "Access forbidden: You do not have permission for this resource"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
