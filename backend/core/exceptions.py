import logging

from django.db import IntegrityError
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger("django")


def custom_exception_handler(exc, context):
    """
    Wraps DRF's default exception handler so every error response has a
    consistent shape: {"detail": "...", "errors": {...optional field errors}}
    and unexpected exceptions (like IntegrityError from a race condition on
    a unique constraint) are converted into clean 400s instead of 500s.
    """
    response = exception_handler(exc, context)

    if response is not None:
        data = {"detail": response.data.get("detail", "Request failed.")}
        if isinstance(response.data, dict) and "detail" not in response.data:
            data = {"detail": "Validation failed.", "errors": response.data}
        response.data = data
        return response

    if isinstance(exc, IntegrityError):
        logger.warning("IntegrityError: %s", exc)
        return Response(
            {"detail": "This record conflicts with an existing entry (duplicate or invalid reference)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    logger.exception("Unhandled exception in %s", context.get("view"))
    return Response(
        {"detail": "An unexpected error occurred. Please try again."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
