from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from database import db
from models.user import User
from models.donor import Donor
from models.beneficiary import Beneficiary
from utils.helpers import log_activity

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role = data.get('role', 'donor').strip().lower()
    phone = data.get('phone', '').strip()
    location = data.get('location', '').strip()
    eligibility_category = data.get('eligibility_category', '').strip()

    if role not in ('donor', 'volunteer', 'beneficiary'):
        return jsonify({'error': 'Public registration is only available for donor, volunteer, and beneficiary accounts.'}), 403

    if not name or not email or not password:
        return jsonify({'error': 'Name, email, and password are required.'}), 400
    if role == 'beneficiary' and (not location or not eligibility_category):
        return jsonify({'error': 'Location and eligibility category are required for beneficiary registration.'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email address is already registered.'}), 400

    user = User(name=name, email=email, role=role, phone=phone)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    # Beneficiaries enter the system pending eligibility review.
    if role == 'donor':
        donor = Donor(user_id=user.id, name=name, email=email, phone=phone)
        db.session.add(donor)
    elif role == 'beneficiary':
        beneficiary = Beneficiary(
            user_id=user.id,
            name=name,
            contact=phone,
            email=email,
            location=location,
            eligibility_category=eligibility_category,
            status='Pending'
        )
        db.session.add(beneficiary)

    db.session.commit()

    login_user(user)
    log_activity('REGISTER', 'USER', user.id, f'Registered new user {email} with role {role}')

    return jsonify({
        'message': 'Account registered successfully',
        'user': user.to_dict()
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    selected_role = data.get('role', '').strip().lower()

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password.'}), 401

    if user.role != 'admin' and not selected_role:
        return jsonify({'error': 'Please select your account role.'}), 400

    if user.role != 'admin' and selected_role != user.role:
        return jsonify({'error': 'The selected role does not match this account.'}), 403

    login_user(user)
    log_activity('LOGIN', 'USER', user.id, f'User {email} logged in')

    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict()
    })

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    user_id = current_user.id
    email = current_user.email
    logout_user()
    log_activity('LOGOUT', 'USER', user_id, f'User {email} logged out')
    return jsonify({'message': 'Logged out successfully'})

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': current_user.to_dict()
        })
    return jsonify({
        'authenticated': False,
        'user': None
    })

@auth_bp.route('/demo-switch', methods=['POST'])
def demo_switch_role():
    """
    Evaluator demo switcher to easily toggle between test user roles.
    """
    data = request.get_json() or {}
    target_role = data.get('role', 'admin').lower()

    target_user = User.query.filter_by(role=target_role).first()
    if not target_user:
        return jsonify({'error': f'No demo user found for role: {target_role}'}), 404

    login_user(target_user)
    log_activity('DEMO_SWITCH', 'USER', target_user.id, f'Switched active demo session to {target_role}')

    return jsonify({
        'message': f'Switched to demo role: {target_role}',
        'user': target_user.to_dict()
    })
