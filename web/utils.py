import re
import string
import logging
from functools import wraps
from flask import request, jsonify, current_app
from werkzeug.security import safe_str_cmp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
VALID_CONTAINER_NAME = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]+$')
VALID_USERNAME = re.compile(r'^[a-zA-Z0-9_-]{3,32}$')
VALID_PASSWORD = re.compile(r'^.{8,128}$')
VALID_PORT = (1, 65535)

# Rate limiting store (in-memory for simplicity, use Redis in production)
_rate_limits = {}

def validate_container_name(name):
    """Validate container name format"""
    if not name or not isinstance(name, str):
        return False
    return bool(VALID_CONTAINER_NAME.match(name))

def validate_username(username):
    """Validate username format"""
    if not username or not isinstance(username, str):
        return False
    return bool(VALID_USERNAME.match(username))

def validate_password(password):
    """Validate password strength"""
    if not password or not isinstance(password, str):
        return False
    return bool(VALID_PASSWORD.match(password))

def validate_port(port):
    """Validate port number"""
    try:
        port = int(port)
        return VALID_PORT[0] <= port <= VALID_PORT[1]
    except (ValueError, TypeError):
        return False

def sanitize_input(input_str, allowed_chars=None):
    """
    Sanitize input string to prevent XSS and injection attacks
    """
    if not input_str or not isinstance(input_str, str):
        return ''
    
    # Remove null bytes
    sanitized = input_str.replace('\x00', '')
    
    # If allowed_chars is specified, only keep those characters
    if allowed_chars:
        sanitized = ''.join(c for c in sanitized if c in allowed_chars)
    
    return sanitized

def rate_limit(requests=100, window=60, key_func=None, scope_func=None):
    """
    Simple rate limiting decorator
    
    Args:
        requests: Number of requests allowed in the time window
        window: Time window in seconds
        key_func: Function to get the rate limit key (defaults to client IP)
        scope_func: Function to get the rate limit scope (e.g., per endpoint)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip rate limiting in debug mode
            if current_app.debug or not current_app.config.get('RATE_LIMIT_ENABLED', True):
                return f(*args, **kwargs)
            
            # Get rate limit key and scope
            key = key_func() if key_func else request.remote_addr
            scope = scope_func() if scope_func else f"{request.endpoint}:{request.method}"
            
            # Initialize rate limit data
            now = int(time.time())
            window_start = now - window
            
            # Clean up old entries
            for k in list(_rate_limits.keys()):
                if _rate_limits[k]['timestamp'] < window_start:
                    _rate_limits.pop(k, None)
            
            # Check rate limit
            rate_key = f"{scope}:{key}"
            if rate_key in _rate_limits:
                if _rate_limits[rate_key]['count'] >= requests:
                    retry_after = _rate_limits[rate_key]['timestamp'] + window - now
                    response = jsonify({
                        'status': 'error',
                        'message': 'Too many requests',
                        'retry_after': retry_after,
                        'code': 'RATE_LIMIT_EXCEEDED'
                    })
                    response.status_code = 429
                    response.headers['Retry-After'] = str(retry_after)
                    return response
                _rate_limits[rate_key]['count'] += 1
            else:
                _rate_limits[rate_key] = {
                    'count': 1,
                    'timestamp': now
                }
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_security_event(event_type, message, user=None, ip=None, details=None):
    """Log security-related events"""
    if not ip:
        ip = request.remote_addr if request else 'unknown'
    if not user and hasattr(request, 'user'):
        user = request.user
    
    log_msg = f"[{event_type}] {message} (user={user}, ip={ip})"
    if details:
        log_msg += f" | Details: {details}"
    
    logger.warning(log_msg)
    
    # In production, you'd also want to send this to a security monitoring system
    if current_app.config.get('SECURITY_EVENT_CALLBACK'):
        try:
            current_app.config['SECURITY_EVENT_CALLBACK'](
                event_type=event_type,
                message=message,
                user=user,
                ip=ip,
                details=details
            )
        except Exception as e:
            logger.error(f"Error in security event callback: {e}")

# Common security headers
def add_security_headers(response):
    """Add security headers to all responses"""
    headers = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; img-src 'self' data:; font-src 'self' data:; connect-src 'self';",
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
        'Cross-Origin-Embedder-Policy': 'require-corp',
        'Cross-Origin-Opener-Policy': 'same-origin',
        'Cross-Origin-Resource-Policy': 'same-site'
    }
    
    # Add headers to response
    for key, value in headers.items():
        if key not in response.headers:
            response.headers[key] = value
    
    return response

# Request ID for better logging
def generate_request_id():
    """Generate a unique request ID"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

def log_request_info():
    """Log request information"""
    request_id = generate_request_id()
    request.request_id = request_id
    
    logger.info(f"[{request_id}] {request.method} {request.path} from {request.remote_addr}")
    
    # Log request body for non-GET requests if needed
    if request.method != 'GET' and request.get_data():
        try:
            logger.debug(f"[{request_id}] Request data: {request.get_data()}")
        except Exception as e:
            logger.error(f"[{request_id}] Failed to log request data: {e}")

def log_response_info(response):
    """Log response information"""
    request_id = getattr(request, 'request_id', 'unknown')
    logger.info(f"[{request_id}] Response: {response.status}")
    return response
