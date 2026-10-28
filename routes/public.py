from flask import Blueprint, jsonify
from models.donation import Donation
from models.distribution import Distribution, DistributionItem
from models.beneficiary import Beneficiary
from models.donor import Donor
from models.inventory import InventoryItem
from models.ledger import LedgerBlock
from utils.blockchain import verify_ledger_integrity
from sqlalchemy import func

public_bp = Blueprint('public', __name__, url_prefix='/api/public')

@public_bp.route('/impact', methods=['GET'])
def get_public_impact():
    # 1. Total Monetary Donated
    total_monetary = Donation.query.filter(
        Donation.type == 'Monetary',
        Donation.status.in_(['Verified', 'Payment Successful'])
    ).with_entities(func.sum(Donation.amount)).scalar() or 0.0

    # 2. Total In-Kind Items Received
    total_inkind_qty = Donation.query.filter_by(type='In-Kind').with_entities(func.sum(Donation.quantity)).scalar() or 0.0

    # 3. Total Beneficiaries Served
    total_beneficiaries = Beneficiary.query.count()

    # 4. Total Distributions Completed
    total_distributions = Distribution.query.count()
    items_distributed_count = DistributionItem.query.with_entities(func.sum(DistributionItem.quantity)).scalar() or 0.0

    # 5. Total Donors count
    total_donors = Donor.query.count()

    # 6. Counts used by the public landing page cards
    total_donations = Donation.query.count()
    total_inventory_items = InventoryItem.query.count()

    # 7. Ledger Integrity Status
    integrity = verify_ledger_integrity()

    # 8. Recent Verified Ledger Blocks (top 5)
    recent_blocks = LedgerBlock.query.order_by(LedgerBlock.index.desc()).limit(5).all()

    return jsonify({
        'impact_summary': {
            'total_monetary_donated': round(total_monetary, 2),
            'total_inkind_quantity': round(total_inkind_qty, 1),
            'total_beneficiaries': total_beneficiaries,
            'total_distributions': total_distributions,
            'total_donations': total_donations,
            'total_inventory_items': total_inventory_items,
            'items_distributed_count': round(items_distributed_count, 1),
            'total_donors': total_donors,
            'ledger_blocks_count': integrity.get('total_blocks', 0),
            'ledger_integrity': {
                'is_valid': integrity.get('is_valid', True),
                'verified_at': integrity.get('verified_at', ''),
                'status_label': '100% Immutable & Verified' if integrity.get('is_valid') else 'INTEGRITY ALERT'
            }
        },
        'recent_verified_blocks': [b.to_dict() for b in recent_blocks]
    })
