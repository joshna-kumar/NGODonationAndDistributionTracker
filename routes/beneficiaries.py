from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from database import db
from models.beneficiary import Beneficiary
from models.aid_request import AidRequest
from utils.auth import role_required
from utils.helpers import log_activity

beneficiaries_bp = Blueprint('beneficiaries', __name__, url_prefix='/api/beneficiaries')


@beneficiaries_bp.route('/requests', methods=['GET'])
@login_required
@role_required('admin', 'staff', 'beneficiary')
def list_aid_requests():
    query = AidRequest.query
    if current_user.role == 'beneficiary':
        beneficiary = Beneficiary.query.filter_by(user_id=current_user.id).first()
        if not beneficiary:
            return jsonify({'requests': []})
        query = query.filter_by(beneficiary_id=beneficiary.id)
    requests = query.order_by(AidRequest.created_at.desc()).all()
    return jsonify({'requests': [aid_request.to_dict() for aid_request in requests]})


@beneficiaries_bp.route('/requests', methods=['POST'])
@login_required
@role_required('beneficiary')
def create_aid_request():
    beneficiary = Beneficiary.query.filter_by(user_id=current_user.id).first()
    if not beneficiary:
        return jsonify({'error': 'Your beneficiary profile is not registered yet.'}), 404

    data = request.get_json(silent=True) or {}
    category = str(data.get('category') or '').strip()
    description = str(data.get('description') or '').strip()
    urgency = str(data.get('urgency') or 'Normal').strip().title()
    if not category or len(category) > 80 or not description or len(description) > 2000:
        return jsonify({'error': 'Choose a request category and provide a description under 2,000 characters.'}), 400
    if urgency not in ('Low', 'Normal', 'High', 'Urgent'):
        return jsonify({'error': 'Urgency must be Low, Normal, High, or Urgent.'}), 400

    aid_request = AidRequest(
        beneficiary_id=beneficiary.id,
        category=category,
        description=description,
        urgency=urgency
    )
    db.session.add(aid_request)
    db.session.commit()
    log_activity('REQUEST', 'AID_REQUEST', aid_request.id, f'{beneficiary.name} requested {category} assistance')
    return jsonify({
        'message': 'Assistance request sent to NGO staff.',
        'request': aid_request.to_dict()
    }), 201


@beneficiaries_bp.route('/requests/<int:request_id>', methods=['PUT'])
@login_required
@role_required('admin', 'staff')
def update_aid_request(request_id):
    aid_request = AidRequest.query.get_or_404(request_id)
    data = request.get_json(silent=True) or {}
    status = str(data.get('status') or '').strip()
    allowed_statuses = ('Under Review', 'Approved', 'Fulfilled', 'Declined')
    if status not in allowed_statuses:
        return jsonify({'error': f'Status must be one of: {", ".join(allowed_statuses)}.'}), 400

    aid_request.status = status
    aid_request.staff_note = str(data.get('staff_note') or '').strip()[:2000]
    aid_request.reviewed_by_id = current_user.id
    db.session.commit()
    log_activity('REVIEW', 'AID_REQUEST', aid_request.id, f'Updated aid request status to {status}')
    return jsonify({'message': 'Assistance request updated.', 'request': aid_request.to_dict()})

@beneficiaries_bp.route('', methods=['GET'])
@login_required
@role_required('admin', 'staff', 'beneficiary', 'auditor')
def list_beneficiaries():
    # If Beneficiary role, show own profile!
    if current_user.role == 'beneficiary':
        ben = Beneficiary.query.filter_by(user_id=current_user.id).first()
        if not ben:
            ben = Beneficiary.query.filter_by(email=current_user.email).first()
        if ben:
            beneficiary_data = ben.to_dict()
            beneficiary_data['distributions'] = [distribution.to_dict() for distribution in ben.distributions]
            return jsonify({'beneficiaries': [beneficiary_data]})
        return jsonify({'beneficiaries': []})

    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    status = request.args.get('status', '').strip()

    query = Beneficiary.query

    if search:
        query = query.filter(
            (Beneficiary.name.ilike(f'%{search}%')) |
            (Beneficiary.location.ilike(f'%{search}%')) |
            (Beneficiary.contact.ilike(f'%{search}%'))
        )

    if category:
        query = query.filter(Beneficiary.eligibility_category == category)

    if status:
        query = query.filter(Beneficiary.status == status)

    beneficiaries = query.order_by(Beneficiary.registered_at.desc()).all()
    return jsonify({'beneficiaries': [b.to_dict() for b in beneficiaries]})

@beneficiaries_bp.route('/<int:ben_id>', methods=['GET'])
@login_required
@role_required('admin', 'staff', 'beneficiary', 'auditor')
def get_beneficiary(ben_id):
    ben = Beneficiary.query.get_or_404(ben_id)

    if current_user.role == 'beneficiary':
        if ben.user_id != current_user.id and ben.email != current_user.email:
            return jsonify({'error': 'Unauthorized'}), 403

    ben_dict = ben.to_dict()
    ben_dict['distributions'] = [d.to_dict() for d in ben.distributions]
    return jsonify({'beneficiary': ben_dict})

@beneficiaries_bp.route('', methods=['POST'])
@login_required
@role_required('admin', 'staff')
def create_beneficiary():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    contact = data.get('contact', '').strip()
    email = data.get('email', '').strip().lower()
    location = data.get('location', '').strip()
    eligibility_category = data.get('eligibility_category', 'General Relief').strip()
    notes = data.get('notes', '').strip()

    if not name or not location:
        return jsonify({'error': 'Name and location are required.'}), 400

    beneficiary = Beneficiary(
        name=name,
        contact=contact,
        email=email,
        location=location,
        eligibility_category=eligibility_category,
        status='Active',
        notes=notes
    )
    db.session.add(beneficiary)
    db.session.commit()

    log_activity('CREATE', 'BENEFICIARY', beneficiary.id, f'Registered beneficiary {name} ({eligibility_category}) in {location}')

    return jsonify({
        'message': 'Beneficiary registered successfully',
        'beneficiary': beneficiary.to_dict()
    }), 201

@beneficiaries_bp.route('/<int:ben_id>', methods=['PUT'])
@login_required
@role_required('admin', 'staff')
def update_beneficiary(ben_id):
    ben = Beneficiary.query.get_or_404(ben_id)
    data = request.get_json() or {}

    ben.name = data.get('name', ben.name).strip()
    ben.contact = data.get('contact', ben.contact).strip()
    ben.email = data.get('email', ben.email).strip().lower()
    ben.location = data.get('location', ben.location).strip()
    ben.eligibility_category = data.get('eligibility_category', ben.eligibility_category).strip()
    ben.status = data.get('status', ben.status).strip()
    ben.notes = data.get('notes', ben.notes).strip()

    db.session.commit()
    log_activity('UPDATE', 'BENEFICIARY', ben.id, f'Updated beneficiary record {ben.name}')

    return jsonify({
        'message': 'Beneficiary updated successfully',
        'beneficiary': ben.to_dict()
    })

@beneficiaries_bp.route('/<int:ben_id>', methods=['DELETE'])
@login_required
@role_required('admin')
def delete_beneficiary(ben_id):
    ben = Beneficiary.query.get_or_404(ben_id)
    name = ben.name
    db.session.delete(ben)
    db.session.commit()

    log_activity('DELETE', 'BENEFICIARY', ben_id, f'Deleted beneficiary {name}')
    return jsonify({'message': f'Beneficiary {name} deleted successfully'})
