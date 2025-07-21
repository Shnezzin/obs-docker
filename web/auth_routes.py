from flask import Blueprint, request, jsonify, session, redirect, url_for, flash, current_app
from functools import wraps
from .auth import auth_manager

# Create auth blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            if request.is_json:
                return jsonify({
                    'status': 'error',
                    'message': 'Username and password are required',
                    'code': 'MISSING_CREDENTIALS'
                }), 400
            flash('Username and password are required', 'error')
            return redirect(url_for('auth.login'))
        
        # Authenticate user
        token = auth_manager.login_user(username, password)
        if not token:
            if request.is_json:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid username or password',
                    'code': 'INVALID_CREDENTIALS'
                }), 401
            flash('Invalid username or password', 'error')
            return redirect(url_for('auth.login'))
        
        # Successful login
        if request.is_json:
            return jsonify({
                'status': 'success',
                'message': 'Login successful',
                'token': token,
                'user': {
                    'username': username,
                    'is_admin': True
                }
            })
        
        next_page = request.args.get('next') or url_for('dashboard')
        return redirect(next_page)
    
    # GET request - show login form
    return '''
        <form method="POST">
            <h2>Login</h2>
            <div>
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div>
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit">Login</button>
        </form>
    '''

@auth_bp.route('/logout')
def logout():
    """Handle user logout"""
    auth_manager.logout_user()
    if request.is_json:
        return jsonify({
            'status': 'success',
            'message': 'Logout successful'
        })
    return redirect(url_for('auth.login'))

@auth_bp.route('/status')
def status():
    """Check authentication status"""
    is_authenticated = 'token' in session and auth_manager.verify_token(session['token'])
    
    if request.is_json:
        return jsonify({
            'status': 'success',
            'authenticated': is_authenticated,
            'user': {
                'username': session.get('username'),
                'is_admin': True
            } if is_authenticated else None
        })
    
    return f"Authenticated: {is_authenticated}"

def login_required(f):
    ""
    Decorator to require authentication for a route.
    Works with both web and API routes.
    """
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
        
        if not token or not auth_manager.verify_token(token):
            if request.path.startswith('/api/'):
                return jsonify({
                    'status': 'error',
                    'message': 'Authentication required',
                    'code': 'AUTH_REQUIRED'
                }), 401
            return redirect(url_for('auth.login', next=request.url))
            
        return f(*args, **kwargs)
    return decorated_function
