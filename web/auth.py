import os
import hmac
import time
from functools import wraps
from flask import request, jsonify, session, current_app
from werkzeug.security import check_password_hash, generate_password_hash

class AuthManager:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize authentication with app configuration"""
        app.config.setdefault('AUTH_ENABLED', True)
        app.config.setdefault('AUTH_TOKEN_EXPIRY', 3600)  # 1 hour
        app.config.setdefault('RATE_LIMIT', "200 per day;50 per hour")
        app.config.setdefault('SESSION_COOKIE_SECURE', True)
        app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
        app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
        
        # Default admin user if not configured
        if 'ADMIN_USERNAME' not in app.config:
            app.config['ADMIN_USERNAME'] = 'admin'
            app.config['ADMIN_PASSWORD_HASH'] = generate_password_hash('admin')
    
    def login_required(self, f):
        """Decorator to require authentication for a route"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_app.config.get('AUTH_ENABLED', True):
                return f(*args, **kwargs)
                
            auth_header = request.headers.get('Authorization')
            token = None
            
            # Check for token in Authorization header
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
            # Fall back to session token
            elif 'token' in session:
                token = session['token']
            
            if not token or not self.verify_token(token):
                if request.path.startswith('/api/'):
                    return jsonify({
                        'status': 'error',
                        'message': 'Authentication required',
                        'code': 'AUTH_REQUIRED'
                    }), 401
                return redirect(url_for('login', next=request.url))
                
            return f(*args, **kwargs)
        return decorated_function
    
    def verify_token(self, token):
        """Verify if token is valid"""
        if not token:
            return False
            
        # In a real app, you'd want to store and validate tokens properly
        # This is a simplified example
        try:
            # Verify token format and expiration
            parts = token.split('.')
            if len(parts) != 3:
                return False
                
            # Check expiration
            expiry = int(parts[1])
            if time.time() > expiry:
                return False
                
            # Verify signature
            message = f"{parts[0]}.{parts[1]}".encode()
            expected_sig = hmac.new(
                current_app.secret_key.encode(),
                message,
                'sha256'
            ).hexdigest()
            
            return hmac.compare_digest(parts[2], expected_sig)
            
        except (ValueError, IndexError):
            return False
    
    def generate_token(self, user_id, expiry_hours=1):
        """Generate a new authentication token"""
        timestamp = int(time.time() + (expiry_hours * 3600))
        message = f"{user_id}.{timestamp}".encode()
        signature = hmac.new(
            current_app.secret_key.encode(),
            message,
            'sha256'
        ).hexdigest()
        return f"{user_id}.{timestamp}.{signature}"
    
    def verify_password(self, username, password):
        """Verify username and password"""
        if not username or not password:
            return False
            
        if username != current_app.config['ADMIN_USERNAME']:
            return False
            
        return check_password_hash(
            current_app.config['ADMIN_PASSWORD_HASH'],
            password
        )
    
    def login_user(self, username, password):
        """Authenticate user and return token"""
        if not self.verify_password(username, password):
            return None
            
        token = self.generate_token(username)
        session['token'] = token
        session['username'] = username
        return token
    
    def logout_user(self):
        """Log out current user"""
        session.pop('token', None)
        session.pop('username', None)
        return True

# Create auth manager instance
auth_manager = AuthManager()
