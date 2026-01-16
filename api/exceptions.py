"""
Custom Exception Handler for API
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        # Customize the response format
        response.data = {
            "error": True,
            "message": str(exc),
            "details": response.data if isinstance(response.data, dict) else {"detail": response.data},
            "status_code": response.status_code
        }
    else:
        # Handle unexpected exceptions
        logger.exception(f"Unhandled exception: {exc}")
        response = Response(
            {
                "error": True,
                "message": "An unexpected error occurred",
                "details": {"exception": str(exc)},
                "status_code": 500
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return response
