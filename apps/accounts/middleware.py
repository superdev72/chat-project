import logging
import time

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("apps.accounts.middleware")


class LoggingMiddleware(MiddlewareMixin):
    """Middleware to log all API calls"""

    def process_request(self, request):
        """Log incoming request"""
        request.start_time = time.time()

        # Log request details
        logger.info(
            f"API Request - Method: {request.method}, "
            f"Path: {request.path}, "
            f"User: {getattr(request.user, 'email', 'Anonymous')}, "
            f"IP: {self.get_client_ip(request)}, "
            f"User-Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')}"
        )

        return None

    def process_response(self, request, response):
        """Log response details"""
        if hasattr(request, "start_time"):
            duration = time.time() - request.start_time

            logger.info(
                f"API Response - Method: {request.method}, "
                f"Path: {request.path}, "
                f"Status: {response.status_code}, "
                f"Duration: {duration:.3f}s, "
                f"User: {getattr(request.user, 'email', 'Anonymous')}"
            )

        return response

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
