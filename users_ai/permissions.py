# permissions.py
# users_ai/permissions.py
from rest_framework.permissions import BasePermission
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class IsMetisToolCallback(BasePermission):
    """
    Allows access only if a valid secret token is provided as a query parameter.
    """

    def has_permission(self, request, view):
        token_in_request = request.query_params.get('metis_secret_token')

        expected_token = settings.METIS_CALLBACK_SECRET_TOKEN

        if not expected_token:
            logger.error("METIS_CALLBACK_SECRET_TOKEN is not set in Django settings. Denying access.")
            return False

        if token_in_request and token_in_request == expected_token:
            logger.info(f"Metis tool callback authenticated for view: {view.__class__.__name__}")
            return True

        logger.warning(
            f"Metis tool callback authentication failed for view: {view.__class__.__name__}. Token in request: '{token_in_request}'")
        return False