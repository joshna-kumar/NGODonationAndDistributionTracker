from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models.ledger import LedgerBlock
from utils.auth import role_required
from utils.blockchain import verify_ledger_integrity, simulate_tamper_block, repair_ledger_hashes
from utils.helpers import log_activity

ledger_bp = Blueprint('ledger', __name__, url_prefix='/api/ledger')

@ledger_bp.route('', methods=['GET'])
@login_required
@role_required('admin', 'staff', 'auditor')
def get_ledger():
    record_type = request.args.get('type', '').strip().upper()
    query = LedgerBlock.query

    if record_type:
        query = query.filter_by(record_type=record_type)

    blocks = query.order_by(LedgerBlock.index.asc()).all()
    return jsonify({
        'blocks': [b.to_dict() for b in blocks],
        'total_blocks': len(blocks)
    })

@ledger_bp.route('/verify', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'staff', 'auditor')
def verify_ledger():
    result = verify_ledger_integrity()
    
    log_activity(
        'VERIFY',
        'LEDGER',
        details=f"Ledger verification result: {'VALID' if result['is_valid'] else 'TAMPERED'} ({result['total_blocks']} blocks checked)"
    )

    return jsonify(result)

@ledger_bp.route('/tamper-demo', methods=['POST'])
@login_required
@role_required('admin')
def tamper_demo():
    """
    Admin action to simulate database tampering for live verification testing.
    """
    data = request.get_json() or {}
    block_index = int(data.get('block_index', 1))
    note = data.get('note', 'Simulated Fraudulent DB Edit')

    success, msg = simulate_tamper_block(block_index, note)
    if success:
        log_activity('TAMPER', 'LEDGER', entity_id=block_index, details=f"Simulated tampering on Block #{block_index}")
        return jsonify({'message': msg, 'tampered_block': block_index})
    return jsonify({'error': msg}), 400

@ledger_bp.route('/repair-demo', methods=['POST'])
@login_required
@role_required('admin')
def repair_demo():
    """
    Admin action to restore valid hashes across all blocks.
    """
    success, msg = repair_ledger_hashes()
    if success:
        log_activity('VERIFY', 'LEDGER', details="Repaired and re-sealed ledger integrity hashes")
        return jsonify({'message': msg})
    return jsonify({'error': msg}), 400
