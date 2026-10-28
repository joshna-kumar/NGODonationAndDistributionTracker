from flask import Blueprint, request, jsonify
from sqlalchemy import func
from flask_login import login_required, current_user
from database import db
from models.distribution import Distribution, DistributionItem
from models.beneficiary import Beneficiary
from models.inventory import InventoryItem, InventoryLog
from models.donation import Donation
from models.donor import Donor
from utils.auth import role_required
from utils.blockchain import add_record_to_ledger
from utils.web3_blockchain import (
    BlockchainTransactionError,
    is_configured,
    record_distribution,
)
from utils.helpers import log_activity

distributions_bp = Blueprint('distributions', __name__, url_prefix='/api/distributions')

@distributions_bp.route('', methods=['GET'])
@login_required
@role_required('admin', 'staff', 'beneficiary', 'auditor', 'donor')
def list_distributions():
    query = Distribution.query

    if current_user.role == 'beneficiary':
        ben = Beneficiary.query.filter_by(user_id=current_user.id).first()
        if not ben:
            ben = Beneficiary.query.filter_by(email=current_user.email).first()
        if ben:
            query = query.filter_by(beneficiary_id=ben.id)
        else:
            return jsonify({'distributions': []})

    if current_user.role == 'donor':
        donor = Donor.query.filter((Donor.user_id == current_user.id) | (Donor.email == current_user.email)).first()
        if donor:
            query = query.join(Donation, Distribution.donation_id == Donation.id).filter(Donation.donor_id == donor.id)
        else:
            return jsonify({'distributions': []})

    search = request.args.get('search', '').strip()
    if search:
        query = query.join(Beneficiary).filter(
            (Beneficiary.name.ilike(f'%{search}%')) |
            (Distribution.location.ilike(f'%{search}%')) |
            (Distribution.notes.ilike(f'%{search}%'))
        )

    distributions = query.order_by(Distribution.date.desc()).all()
    return jsonify({'distributions': [d.to_dict() for d in distributions]})

@distributions_bp.route('/<int:dist_id>', methods=['GET'])
@login_required
@role_required('admin', 'staff', 'beneficiary', 'auditor', 'donor')
def get_distribution(dist_id):
    dist = Distribution.query.get_or_404(dist_id)

    if current_user.role == 'beneficiary':
        if not dist.beneficiary or (dist.beneficiary.user_id != current_user.id and dist.beneficiary.email != current_user.email):
            return jsonify({'error': 'Unauthorized'}), 403

    if current_user.role == 'donor':
        donor = Donor.query.filter((Donor.user_id == current_user.id) | (Donor.email == current_user.email)).first()
        if not donor or not dist.donation or dist.donation.donor_id != donor.id:
            return jsonify({'error': 'Unauthorized'}), 403

    return jsonify({'distribution': dist.to_dict()})

@distributions_bp.route('', methods=['POST'])
@login_required
@role_required('admin', 'staff')
def create_distribution():
    data = request.get_json() or {}
    beneficiary_id = data.get('beneficiary_id')
    location = data.get('location', '').strip()
    notes = data.get('notes', '').strip()
    items_data = data.get('items', []) # Array of { inventory_item_id, quantity }
    amount = float(data.get('amount') or 0.0)

    if not beneficiary_id:
        return jsonify({'error': 'Beneficiary selection is required.'}), 400

    beneficiary = Beneficiary.query.get(beneficiary_id)
    if not beneficiary:
        return jsonify({'error': 'Selected beneficiary does not exist.'}), 404

    # Monetary aid validation
    if amount > 0:
        available_money = 0.0
        total_monetary = Donation.query.filter(
            Donation.type == 'Monetary',
            Donation.status.in_(['Verified', 'Payment Successful'])
        ).with_entities(func.sum(Donation.amount)).scalar() or 0.0
        allocated_money = Distribution.query.with_entities(func.sum(Distribution.amount)).scalar() or 0.0
        available_money = total_monetary - allocated_money
        if amount > available_money + 1e-9:
            return jsonify({'error': f'Insufficient monetary stock. Available: ₹{available_money:.2f}'}), 400

    if not items_data or len(items_data) == 0:
        if amount <= 0:
            return jsonify({'error': 'At least one inventory item or a monetary amount must be provided.'}), 400

    # 1. Stock Validation Phase
    validated_items = []
    for item_req in items_data:
        item_id = item_req.get('inventory_item_id')
        qty = float(item_req.get('quantity') or 0.0)
        
        if qty <= 0:
            continue

        inv_item = InventoryItem.query.get(item_id)
        if not inv_item:
            return jsonify({'error': f'Inventory item ID {item_id} not found.'}), 404

        if inv_item.quantity < qty:
            return jsonify({
                'error': f'Insufficient stock for "{inv_item.name}". Requested: {qty} {inv_item.unit}, Available: {inv_item.quantity} {inv_item.unit}'
            }), 400

        validated_items.append((inv_item, qty))

    if not validated_items and amount <= 0:
        return jsonify({'error': 'No valid item quantities specified.'}), 400

    donation_id = data.get('donation_id')
    if donation_id:
        donation_id = int(donation_id)
        if not Donation.query.get(donation_id):
            return jsonify({'error': 'Selected donation does not exist.'}), 404
    else:
        if validated_items:
            source_log = InventoryLog.query.filter(
                InventoryLog.inventory_item_id == validated_items[0][0].id,
                InventoryLog.reference_type == 'DONATION',
            ).order_by(InventoryLog.timestamp.desc()).first()
            donation_id = source_log.reference_id if source_log else None
        else:
            donation_id = None
        if not donation_id:
            latest_donation = Donation.query.order_by(Donation.date.desc()).first()
            donation_id = latest_donation.id if latest_donation else None

    # 2. Create Distribution Header Record
    distribution = Distribution(
        beneficiary_id=beneficiary.id,
        donation_id=donation_id,
        staff_id=current_user.id,
        location=location or beneficiary.location,
        notes=notes,
        status='Completed',
        amount=amount
    )
    db.session.add(distribution)
    db.session.flush() # obtain dist.id

    # 3. Process Distribution Items and Deduct Inventory
    distributed_summary = []
    for inv_item, qty in validated_items:
        dist_item = DistributionItem(
            distribution_id=distribution.id,
            inventory_item_id=inv_item.id,
            quantity=qty
        )
        db.session.add(dist_item)

        # Deduct stock
        inv_item.quantity -= qty

        # Log movement
        inv_log = InventoryLog(
            inventory_item_id=inv_item.id,
            movement_type='OUTBOUND',
            quantity=qty,
            reference_type='DISTRIBUTION',
            reference_id=distribution.id,
            notes=f'Distributed to {beneficiary.name} ({beneficiary.eligibility_category})'
        )
        db.session.add(inv_log)

        distributed_summary.append(f"{qty} {inv_item.unit} of {inv_item.name}")

    if amount > 0:
        distributed_summary.append(f"₹{amount:.2f} monetary aid")

    # 4. Record the distribution on the configured local blockchain.
    blockchain_status = 'not_configured'
    blockchain_transaction_hash = ''
    if is_configured() and validated_items:
        try:
            blockchain_result = record_distribution(
                distribution.id,
                distribution.donation_id or 0,
                beneficiary.id,
                sum(quantity for _, quantity in validated_items),
            )
            blockchain_transaction_hash = blockchain_result['transaction_hash']
            distribution.blockchain_transaction_hash = blockchain_transaction_hash
            blockchain_status = 'recorded'
        except BlockchainTransactionError as error:
            db.session.rollback()
            return jsonify({'error': f'Blockchain transaction failed: {error}'}), 502

    # 5. Write the local SHA-256 audit ledger entry.
    ledger_payload = {
        'distribution_id': distribution.id,
        'donation_id': distribution.donation_id,
        'beneficiary_id': beneficiary.id,
        'items': ", ".join(distributed_summary),
    }

    block = add_record_to_ledger('DISTRIBUTION', distribution.id, ledger_payload)
    distribution.block_hash = block.block_hash

    db.session.commit()

    log_activity('CREATE', 'DISTRIBUTION', distribution.id, f'Completed distribution to {beneficiary.name} in {location} (Block #{block.index})')

    return jsonify({
        'message': 'Distribution recorded, stock updated, and immutably sealed in blockchain ledger!',
        'distribution': distribution.to_dict(),
        'block_index': block.index,
        'block_hash': block.block_hash,
        'blockchain_status': blockchain_status,
        'blockchain_transaction_hash': blockchain_transaction_hash
    }), 201
