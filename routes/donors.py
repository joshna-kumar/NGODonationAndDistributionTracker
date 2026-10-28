from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from database import db
from models.donor import Donor
from utils.auth import role_required
from utils.helpers import log_activity, find_duplicate_donors

donors_bp = Blueprint('donors', __name__, url_prefix='/api/donors')

@donors_bp.route('', methods=['GET'])
@login_required
@role_required('admin', 'staff', 'auditor')
def list_donors():
    search = request.args.get('search', '').strip()
    query = Donor.query

    if search:
        query = query.filter(
            (Donor.name.ilike(f'%{search}%')) |
            (Donor.email.ilike(f'%{search}%')) |
            (Donor.phone.ilike(f'%{search}%')) |
            (Donor.preferred_causes.ilike(f'%{search}%'))
        )

    donors = query.order_by(Donor.created_at.desc()).all()
    return jsonify({'donors': [d.to_dict() for d in donors]})

@donors_bp.route('/<int:donor_id>', methods=['GET'])
@login_required
@role_required('admin', 'staff', 'auditor', 'volunteer')
def get_donor(donor_id):
    donor = Donor.query.get_or_404(donor_id)
    
    # If role is donor, check ownership
    if current_user.role == 'donor' and donor.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized to view this donor profile'}), 403

    donor_dict = donor.to_dict()
    donor_dict['donations'] = [d.to_dict() for d in donor.donations]
    return jsonify({'donor': donor_dict})

@donors_bp.route('', methods=['POST'])
@login_required
@role_required('admin', 'staff')
def create_donor():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    phone = data.get('phone', '').strip()
    address = data.get('address', '').strip()
    preferred_causes = data.get('preferred_causes', 'General Fund').strip()

    if not name or not email:
        return jsonify({'error': 'Name and email are required fields.'}), 400

    # Duplicate check warning
    duplicates = find_duplicate_donors(name=name, email=email, phone=phone)
    if duplicates and not data.get('force'):
        return jsonify({
            'warning': 'Potential duplicate donor detected',
            'duplicates': duplicates,
            'require_force': True
        }), 409

    donor = Donor(
        name=name,
        email=email,
        phone=phone,
        address=address,
        preferred_causes=preferred_causes,
        total_donated=0.0
    )
    db.session.add(donor)
    db.session.commit()

    log_activity('CREATE', 'DONOR', donor.id, f'Created donor record for {name} ({email})')

    return jsonify({
        'message': 'Donor created successfully',
        'donor': donor.to_dict()
    }), 201

@donors_bp.route('/<int:donor_id>', methods=['PUT'])
@login_required
@role_required('admin', 'staff')
def update_donor(donor_id):
    donor = Donor.query.get_or_404(donor_id)
    data = request.get_json() or {}

    donor.name = data.get('name', donor.name).strip()
    donor.email = data.get('email', donor.email).strip().lower()
    donor.phone = data.get('phone', donor.phone).strip()
    donor.address = data.get('address', donor.address).strip()
    donor.preferred_causes = data.get('preferred_causes', donor.preferred_causes).strip()

    db.session.commit()
    log_activity('UPDATE', 'DONOR', donor.id, f'Updated donor profile {donor.name}')

    return jsonify({
        'message': 'Donor updated successfully',
        'donor': donor.to_dict()
    })

@donors_bp.route('/<int:donor_id>', methods=['DELETE'])
@login_required
@role_required('admin')
def delete_donor(donor_id):
    donor = Donor.query.get_or_404(donor_id)
    name = donor.name
    db.session.delete(donor)
    db.session.commit()

    log_activity('DELETE', 'DONOR', donor_id, f'Deleted donor {name}')
    return jsonify({'message': f'Donor {name} deleted successfully'})

@donors_bp.route('/check-duplicates', methods=['POST'])
@login_required
@role_required('admin', 'staff')
def check_duplicates():
    data = request.get_json() or {}
    name = data.get('name', '')
    email = data.get('email', '')
    phone = data.get('phone', '')
    exclude_id = data.get('exclude_id')

    duplicates = find_duplicate_donors(name=name, email=email, phone=phone, exclude_id=exclude_id)
    return jsonify({'has_duplicates': len(duplicates) > 0, 'duplicates': duplicates})
