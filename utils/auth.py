from functools import wraps
from flask import jsonify
from flask_login import current_user

def role_required(*allowed_roles):
    """
    Decorator enforcing Role-Based Access Control (RBAC).
    Allowed roles can be 'admin', 'staff', 'donor', 'beneficiary', 'auditor'.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Unauthorized. Please log in.'}), 401
            
            # Admin has access to all routes unless restricted
            if current_user.role == 'admin':
                return f(*args, **kwargs)

            if current_user.role not in allowed_roles:
                return jsonify({
                    'error': f'Forbidden access. Required role: {", ".join(allowed_roles)}. Your role: {current_user.role}'
                }), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator
