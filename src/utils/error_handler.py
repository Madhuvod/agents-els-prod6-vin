"""
Centralized error handling utilities for the simulation API.

This module provides consistent error handling patterns and standardized
error response formats across all API endpoints.
"""

import logging
from typing import Any, Dict, Optional, Union
from enum import Enum
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorType(str, Enum):
    """Standard error types for the simulation API."""
    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    NOT_FOUND_ERROR = "not_found_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    EXTERNAL_API_ERROR = "external_api_error"
    INTERNAL_ERROR = "internal_error"
    SIMULATION_ERROR = "simulation_error"
    SCHEMA_ERROR = "schema_error"


class StandardErrorResponse(BaseModel):
    """Standard error response format for all API endpoints."""
    error: Dict[str, Any]
    
    @classmethod
    def create(
        cls,
        message: str,
        error_type: ErrorType = ErrorType.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
        code: Optional[str] = None
    ) -> "StandardErrorResponse":
        """Create a standardized error response."""
        error_data = {
            "message": message,
            "type": error_type.value
        }
        
        if code:
            error_data["code"] = code
            
        if details:
            error_data["details"] = details
            
        return cls(error=error_data)


class SimulationAPIException(Exception):
    """Base exception class for simulation API errors."""
    
    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.INTERNAL_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        code: Optional[str] = None
    ):
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.details = details or {}
        self.code = code
        super().__init__(message)
    
    def to_response(self) -> JSONResponse:
        """Convert exception to standardized JSON response."""
        error_response = StandardErrorResponse.create(
            message=self.message,
            error_type=self.error_type,
            details=self.details,
            code=self.code
        )
        return JSONResponse(
            content=error_response.model_dump(),
            status_code=self.status_code
        )


class ValidationException(SimulationAPIException):
    """Exception for validation errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_type=ErrorType.VALIDATION_ERROR,
            status_code=422,
            details=details
        )


class AuthenticationException(SimulationAPIException):
    """Exception for authentication errors."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_type=ErrorType.AUTHENTICATION_ERROR,
            status_code=401
        )


class ExternalAPIException(SimulationAPIException):
    """Exception for external API errors (e.g., LLM providers)."""
    
    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        original_error: Optional[str] = None
    ):
        details = {}
        if provider:
            details["provider"] = provider
        if original_error:
            details["original_error"] = original_error
            
        super().__init__(
            message=message,
            error_type=ErrorType.EXTERNAL_API_ERROR,
            status_code=502,
            details=details
        )


class SimulationException(SimulationAPIException):
    """Exception for simulation-specific errors."""
    
    def __init__(
        self,
        message: str,
        simulation_id: Optional[str] = None,
        turn_number: Optional[int] = None
    ):
        details = {}
        if simulation_id:
            details["simulation_id"] = simulation_id
        if turn_number is not None:
            details["turn_number"] = turn_number
            
        super().__init__(
            message=message,
            error_type=ErrorType.SIMULATION_ERROR,
            status_code=400,
            details=details
        )


def handle_litellm_error(error: Exception, context: str = "") -> JSONResponse:
    """
    Handle errors from LiteLLM library with consistent formatting.
    
    Args:
        error: The original LiteLLM exception
        context: Additional context about where the error occurred
        
    Returns:
        Standardized JSON error response
    """
    from litellm.exceptions import APIConnectionError, AuthenticationError
    
    if isinstance(error, AuthenticationError):
        exc = AuthenticationException(str(error))
    elif isinstance(error, APIConnectionError):
        exc = ExternalAPIException(
            message=f"External API connection failed: {str(error)}",
            provider="LLM Provider",
            original_error=str(error)
        )
    else:
        exc = SimulationAPIException(
            message=f"LLM API error: {str(error)}",
            error_type=ErrorType.EXTERNAL_API_ERROR,
            status_code=500
        )
    
    # Log the error with context
    logger = logging.getLogger(__name__)
    logger.error(f"LiteLLM error in {context}: {str(error)}", exc_info=True)
    
    return exc.to_response()


def log_error(
    error: Exception,
    context: str,
    extra_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log errors with consistent formatting and context.
    
    Args:
        error: The exception that occurred
        context: Description of where the error occurred
        extra_data: Additional data to include in the log
    """
    logger = logging.getLogger(__name__)
    
    log_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context
    }
    
    if extra_data:
        log_data.update(extra_data)
    
    logger.error(f"Error in {context}: {str(error)}", extra=log_data, exc_info=True)


def create_error_response(
    message: str,
    status_code: int = 500,
    error_type: ErrorType = ErrorType.INTERNAL_ERROR,
    details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """
    Create a standardized error response.
    
    Args:
        message: Error message
        status_code: HTTP status code
        error_type: Type of error
        details: Additional error details
        
    Returns:
        Standardized JSON error response
    """
    error_response = StandardErrorResponse.create(
        message=message,
        error_type=error_type,
        details=details
    )
    
    return JSONResponse(
        content=error_response.model_dump(),
        status_code=status_code
    )