from flask import Blueprint, request, jsonify
from flask_login import login_required
from models.audit import ActivityLog
from utils.auth import role_required

audit_bp = Blueprint('audit', __name__, url_prefix='/api/audit')

@audit_bp.route('', methods=['GET'])
@login_required
@role_required('admin', 'auditor')
def get_audit_logs():
    entity = request.args.get('entity', '').strip().upper()
    action = request.args.get('action', '').strip().upper()
    user_search = request.args.get('user', '').strip()

    query = ActivityLog.query

    if entity:
        query = query.filter_by(entity=entity)

    if action:
        query = query.filter_by(action=action)

    if user_search:
        query = query.filter(ActivityLog.user_name.ilike(f'%{user_search}%'))

    logs = query.order_by(ActivityLog.timestamp.desc()).limit(150).all()
    return jsonify({'logs': [l.to_dict() for l in logs]})
