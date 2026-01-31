"""Error handling utilities

This module provides utilities for filtering internal errors
to prevent exposing sensitive information to end users.
"""

import re

# Keywords that indicate an internal error that should not be exposed to users
INTERNAL_ERROR_KEYWORDS = [
    # Authentication/Authorization errors
    '401', 'unauthorized', 'authentication', 'authorization',
    'bearer', 'token', 'credential', 'invalid token',
    # Chinese equivalents
    '验证失败', '认证失败', '凭据', '令牌',
    # API errors
    'api 请求失败', 'api请求失败', 'api error', 'api request failed',
    # Rate limiting
    '速率限制', 'rate limit', 'too many requests', '429',
    # Access errors
    '403', 'forbidden', 'access denied',
    # Cloudflare/Security
    'cloudflare', 'cf ', 'cf_', 'challenge',
    # Sentinel token
    'sentinel', 'openai-sentinel',
    # Internal service errors
    'internal server', '内部错误', 'upstream',
    # Network/Connection errors that might expose infrastructure
    'proxy', 'connection refused', 'timeout', 'dns',
]

# Default messages for users
DEFAULT_ERROR_MESSAGES = {
    'video': 'Video generation temporarily unavailable. Please try again later.',
    'image': 'Image generation temporarily unavailable. Please try again later.',
    'general': 'Service temporarily unavailable. Please try again later.',
    'api': 'Request failed. Please try again later.',
}


def is_internal_error(error_message: str) -> bool:
    """Check if an error message contains internal error indicators
    
    Args:
        error_message: The error message to check
        
    Returns:
        True if the error appears to be an internal error
    """
    if not error_message:
        return False
    
    error_lower = error_message.lower()
    return any(keyword in error_lower for keyword in INTERNAL_ERROR_KEYWORDS)


def filter_error_message(
    error: Exception,
    error_type: str = 'general',
    preserve_patterns: list = None
) -> str:
    """Filter error message to hide internal details from users
    
    Args:
        error: The exception that was raised
        error_type: Type of error for selecting default message ('video', 'image', 'general', 'api')
        preserve_patterns: List of patterns that should NOT be filtered (e.g., content policy violations)
        
    Returns:
        A user-friendly error message
    """
    error_str = str(error)
    error_lower = error_str.lower()
    
    # Check if this error should be preserved (e.g., content policy violations)
    if preserve_patterns:
        for pattern in preserve_patterns:
            if pattern.lower() in error_lower:
                return error_str
    
    # Check for user-friendly errors that should be passed through
    user_friendly_patterns = [
        'content policy',
        'content violation',
        'guardrail',
        'inappropriate',
        'not allowed',
        'violates',
        'generation timeout',  # Timeout is okay to show
        'task not found',
        'not found',
        'invalid model',
        'invalid parameter',
        'missing required',
        'prompt is required',
    ]
    
    for pattern in user_friendly_patterns:
        if pattern in error_lower:
            return error_str
    
    # Check if it's an internal error
    if is_internal_error(error_str):
        return DEFAULT_ERROR_MESSAGES.get(error_type, DEFAULT_ERROR_MESSAGES['general'])
    
    # If not recognized as internal, return original message
    return error_str


def get_safe_error_response(
    error: Exception,
    error_type: str = 'general',
    include_code: bool = True
) -> dict:
    """Get a safe error response dict for API responses
    
    Args:
        error: The exception that was raised
        error_type: Type of error ('video', 'image', 'general', 'api')
        include_code: Whether to include error code in response
        
    Returns:
        Dictionary suitable for JSON response
    """
    message = filter_error_message(error, error_type)
    
    response = {"message": message}
    
    if include_code:
        error_str = str(error).lower()
        if 'policy' in error_str or 'violation' in error_str:
            response["code"] = "content_policy_violation"
        elif 'timeout' in error_str:
            response["code"] = "timeout"
        elif 'not found' in error_str:
            response["code"] = "not_found"
        else:
            response["code"] = "server_error"
    
    return response


def _extract_http_status(message: str):
    """Extract HTTP status code from an error message if present."""
    if not message:
        return None
    match = re.search(r'(?:http\s*|status\s*code\s*|^)(\d{3})', message, re.IGNORECASE)
    if match:
        try:
            code = int(match.group(1))
            if 100 <= code <= 599:
                return code
        except ValueError:
            return None
    return None


def classify_error_source(message: str) -> str:
    """Classify error source for admin logs (proxy/network/upstream/python)."""
    if not message:
        return "python"
    lower = message.lower()
    if any(k in lower for k in ["proxy", "socks", "tunnel", "proxyconnect"]):
        return "proxy"
    if any(k in lower for k in ["cloudflare", "cf challenge", "cf_"]):
        return "cloudflare"
    if any(k in lower for k in ["rate limit", "too many requests", "429"]):
        return "rate_limit"
    if any(k in lower for k in ["unauthorized", "invalid token", "credential", "401", "403", "forbidden"]):
        return "auth"
    if any(k in lower for k in ["timeout", "timed out", "deadline", "read timeout"]):
        return "timeout"
    if any(k in lower for k in ["connection refused", "connection reset", "dns", "network", "ssl"]):
        return "network"
    if any(k in lower for k in ["http", "status code", "bad gateway", "upstream"]):
        return "upstream"
    return "python"


def build_error_detail(error: Exception, source_hint: str = None) -> dict:
    """Build detailed error payload for admin logs."""
    message = str(error) if error is not None else ""
    detail = {
        "error": message,
        "error_type": type(error).__name__ if error is not None else "Error",
        "error_source": source_hint or classify_error_source(message)
    }
    http_status = _extract_http_status(message)
    if http_status:
        detail["http_status"] = http_status
    return detail
