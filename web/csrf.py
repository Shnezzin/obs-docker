import os
import hmac
import hashlib
import time
import secrets
from functools import wraps
from flask import request, jsonify, session, current_app, g
from werkzeug.security import safe_str_cmp

class CSRFProtect:
    def __init__(self, app=None):
        self._exempt_views = set()
        self._exempt_blueprints = set()
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the CSRF protection for the application"""
        app.config.setdefault('WTF_CSRF_ENABLED', True)
        app.config.setdefault('WTF_CSRF_SECRET_KEY', os.urandom(24))
        app.config.setdefault('WTF_CSRF_TIME_LIMIT', 3600)  # 1 hour
        app.config.setdefault('WTF_CSRF_HEADERS', ['X-CSRFToken', 'X-CSRF-Token'])
        app.config.setdefault('WTF_CSRF_SSL_STRICT', True)
        app.config.setdefault('WTF_CSRF_HTTP_REFERER', True)
        app.config.setdefault('WTF_CSRF_METHODS', ['POST', 'PUT', 'PATCH', 'DELETE'])
        
        # Add before request handler
        app.before_request(self._csrf_checks)
        
        # Add after request handler to set CSRF token in response
        app.after_request(self._set_csrf_cookie)
        
        # Add template global for generating CSRF tokens in forms
        app.jinja_env.globals['csrf_token'] = self.generate_csrf_token
    
    def _get_csrf_token(self):
        """Get the current CSRF token or generate a new one"""
        if '_csrf_token' not in session:
            session['_csrf_token'] = self._generate_token()
        return session['_csrf_token']
    
    def _generate_token(self):
        """Generate a new CSRF token"""
        return hashlib.sha1(os.urandom(64)).hexdigest()
    
    def generate_csrf_token(self):
        """Generate a CSRF token for forms"""
        return self._get_csrf_token()
    
    def _set_csrf_cookie(self, response):
        """Set the CSRF token in a cookie if not already set"""
        if not current_app.config['WTF_CSRF_ENABLED']:
            return response
            
        if not request.endpoint or request.endpoint in self._exempt_views:
            return response
            
        if hasattr(g, 'csrf_exempt') and g.csrf_exempt:
            return response
            
        # Set cookie if not already set
        if not request.cookies.get('XSRF-TOKEN'):
            response.set_cookie(
                'XSRF-TOKEN',
                self._get_csrf_token(),
                httponly=False,  # Allow JavaScript to read the cookie
                secure=current_app.config.get('SESSION_COOKIE_SECURE', True),
                samesite='Strict',
                max_age=current_app.config['WTF_CSRF_TIME_LIMIT']
            )
        return response
    
    def _csrf_checks(self):
        """Perform CSRF validation"""
        if not current_app.config['WTF_CSRF_ENABLED']:
            return
            
        # Skip CSRF checks for exempted views
        if request.endpoint in self._exempt_views:
            return
            
        # Skip CSRF checks for exempted blueprints
        if request.blueprint in self._exempt_blueprints:
            return
            
        # Skip CSRF checks for exempted methods
        if request.method not in current_app.config['WTF_CSRF_METHODS']:
            return
            
        # Skip if marked as exempt
        if hasattr(g, 'csrf_exempt') and g.csrf_exempt:
            return
            
        # Get token from form data or headers
        token = None
        
        # Check form data first
        if request.is_json and request.get_json(silent=True):
            token = request.get_json().get('csrf_token')
        elif request.form:
            token = request.form.get('csrf_token')
        
        # Then check headers
        if not token:
            for header_name in current_app.config['WTF_CSRF_HEADERS']:
                token = request.headers.get(header_name)
                if token:
                    break
        
        # Check cookie as last resort (for AJAX requests)
        if not token and request.cookies.get('XSRF-TOKEN'):
            token = request.cookies.get('XSRF-TOKEN')
        
        # Get session token
        session_token = self._get_csrf_token()
        
        # Compare tokens
        if not token or not self._compare_tokens(token, session_token):
            current_app.logger.warning(
                f"CSRF validation failed for {request.endpoint} - "
                f"Token: {'present' if token else 'missing'}, "
                f"Session: {session_token}"
            )
            return self._csrf_failure_response()
    
    def _compare_tokens(self, token1, token2):
        """Compare two tokens in a timing-safe manner"""
        if not token1 or not token2:
            return False
            
        try:
            return hmac.compare_digest(token1, token2)
        except (TypeError, AttributeError):
            return False
    
    def _csrf_failure_response(self):
        """Generate a CSRF failure response"""
        if request.is_json or request.content_type == 'application/json':
            return jsonify({
                'status': 'error',
                'message': 'The CSRF token is missing or invalid',
                'code': 'CSRF_VALIDATION_FAILED'
            }), 403
        
        from flask import render_template_string
        return render_template_string("""
            <h1>CSRF Validation Failed</h1>
            <p>The CSRF token is missing or invalid.</p>
            <p><a href="{{ url_for('auth.login') }}">Return to login</a></p>
        """), 403
    
    def exempt(self, view):
        """Decorator to exempt a view from CSRF protection"""
        if isinstance(view, str):
            view = current_app.view_functions[view]
        
        self._exempt_views.add(view.__name__)
        return view
    
    def exempt_blueprint(self, bp):
        """Exempt all views in a blueprint from CSRF protection"""
        self._exempt_blueprints.add(bp.name)
        return bp
    
    def get_csrf_token(self):
        """Get the current CSRF token (for API use)"""
        return self._get_csrf_token()

# Create CSRF protection instance
csrf = CSRFProtect()

def csrf_protect(f):
    ""
    Decorator for views that require CSRF protection.
    Use this for API endpoints that need CSRF protection.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_app.config.get('WTF_CSRF_ENABLED', True):
            return f(*args, **kwargs)
            
        if request.method in current_app.config.get('WTF_CSRF_METHODS', ['POST', 'PUT', 'PATCH', 'DELETE']):
            token = None
            
            # Get token from form data or headers
            if request.is_json and request.get_json(silent=True):
                token = request.get_json().get('csrf_token')
            elif request.form:
                token = request.form.get('csrf_token')
            
            if not token:
                for header_name in current_app.config.get('WTF_CSRF_HEADERS', []):
                    token = request.headers.get(header_name)
                    if token:
                        break
            
            # Get session token
            session_token = csrf.get_csrf_token()
            
            # Compare tokens
            if not token or not hmac.compare_digest(token, session_token):
                return jsonify({
                    'status': 'error',
                    'message': 'The CSRF token is missing or invalid',
                    'code': 'CSRF_VALIDATION_FAILED'
                }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function
