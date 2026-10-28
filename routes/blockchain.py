from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from database import db
from models.donation import Donation
from models.distribution import Distribution
from utils.auth import role_required
from utils.web3_blockchain import (
    BlockchainNotConfigured,
    BlockchainTransactionError,
    get_distribution,
    is_configured,
    record_distribution,
)

blockchain_bp = Blueprint('blockchain', __name__, url_prefix='/api/blockchain')


@blockchain_bp.route('/record', methods=['POST'])
@login_required
@role_required('admin', 'staff')
def record_distribution_transaction():
    if not is_configured():
        return jsonify({'error': 'Real blockchain is not configured. See blockchain/README.md.'}), 503

    data = request.get_json() or {}
    distribution_id = data.get('distribution_id')
    distribution = Distribution.query.get(distribution_id) if distribution_id else None
    if not distribution:
        return jsonify({'error': 'Distribution not found.'}), 404
    if distribution.blockchain_transaction_hash:
        return jsonify({
            'message': 'Distribution is already recorded on the blockchain.',
            'transaction_hash': distribution.blockchain_transaction_hash,
        })

    if not distribution.donation_id:
        latest_donation = Donation.query.order_by(Donation.date.desc()).first()
        distribution.donation_id = latest_donation.id if latest_donation else None

    amount = sum(item.quantity for item in distribution.items)
    try:
        result = record_distribution(
            distribution.id,
            distribution.donation_id or 0,
            distribution.beneficiary_id,
            amount,
        )
        distribution.blockchain_transaction_hash = result['transaction_hash']
        db.session.commit()
        return jsonify({
            'message': 'Distribution recorded on the blockchain.',
            'distribution_id': distribution.id,
            **result,
        }), 201
    except (BlockchainNotConfigured, BlockchainTransactionError) as error:
        db.session.rollback()
        return jsonify({'error': f'Blockchain transaction failed: {error}'}), 502


@blockchain_bp.route('/<transaction_id>', methods=['GET'])
@login_required
@role_required('admin', 'staff', 'auditor', 'beneficiary')
def get_distribution_transaction(transaction_id):
    distribution = Distribution.query.filter_by(blockchain_transaction_hash=transaction_id).first()
    if not distribution and transaction_id.isdigit():
        distribution = Distribution.query.get(int(transaction_id))
    if not distribution:
        return jsonify({'error': 'Distribution not found.'}), 404

    if current_user.role == 'beneficiary':
        beneficiary = distribution.beneficiary
        if not beneficiary or beneficiary.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized.'}), 403

    if not distribution.blockchain_transaction_hash:
        return jsonify({'error': 'This distribution has no blockchain transaction hash.'}), 404

    try:
        record = get_distribution(distribution.id)
        return jsonify({
            'transaction_hash': distribution.blockchain_transaction_hash,
            'record': record,
        })
    except (BlockchainNotConfigured, BlockchainTransactionError) as error:
        return jsonify({'error': str(error)}), 503
