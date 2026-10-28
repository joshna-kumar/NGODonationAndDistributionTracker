from flask import Blueprint, request, Response, jsonify
from flask_login import login_required
from models.donation import Donation
from models.donor import Donor
from models.inventory import InventoryItem
from models.distribution import Distribution
from models.beneficiary import Beneficiary
from models.ledger import LedgerBlock
from utils.auth import role_required
from sqlalchemy import func
import csv
import io
from datetime import datetime

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

@reports_bp.route('/analytics', methods=['GET'])
@login_required
@role_required('admin', 'staff', 'auditor')
def get_analytics():
    # 1. Category breakdown for Donations
    cat_donations = Donation.query.with_entities(
        Donation.category,
        func.sum(Donation.amount),
        func.sum(Donation.quantity),
        func.count(Donation.id)
    ).group_by(Donation.category).all()

    category_labels = [c[0] for c in cat_donations]
    category_amounts = [round((c[1] or 0.0) or (c[2] or 0.0), 2) for c in cat_donations]
    category_counts = [c[3] for c in cat_donations]

    # 2. Inventory Stock Levels & Low-Stock status
    inv_items = InventoryItem.query.order_by(InventoryItem.quantity.asc()).limit(10).all()
    inv_names = [i.name for i in inv_items]
    inv_quantities = [i.quantity for i in inv_items]
    inv_thresholds = [i.low_stock_threshold for i in inv_items]

    # 3. Top Donors
    top_donors_db = Donor.query.order_by(Donor.total_donated.desc()).limit(5).all()
    top_donors = [{
        'name': d.name,
        'total_donated': d.total_donated,
        'causes': d.preferred_causes
    } for d in top_donors_db]

    # 4. Beneficiaries Served by Eligibility Category
    ben_cat = Beneficiary.query.with_entities(
        Beneficiary.eligibility_category,
        func.count(Beneficiary.id)
    ).group_by(Beneficiary.eligibility_category).all()

    ben_cat_labels = [b[0] for b in ben_cat]
    ben_cat_counts = [b[1] for b in ben_cat]

    return jsonify({
        'donations_by_category': {
            'labels': category_labels,
            'amounts': category_amounts,
            'counts': category_counts
        },
        'inventory_levels': {
            'labels': inv_names,
            'quantities': inv_quantities,
            'thresholds': inv_thresholds
        },
        'top_donors': top_donors,
        'beneficiaries_by_category': {
            'labels': ben_cat_labels,
            'counts': ben_cat_counts
        }
    })

@reports_bp.route('/export-csv', methods=['GET'])
@login_required
@role_required('admin', 'staff', 'auditor')
def export_csv():
    report_type = request.args.get('type', 'donations').lower()

    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == 'donations':
        writer.writerow(['Donation ID', 'Donor Name', 'Donor Email', 'Type', 'Category', 'Amount/Qty', 'Unit', 'Status', 'Date', 'Block Hash'])
        donations = Donation.query.order_by(Donation.date.desc()).all()
        for d in donations:
            writer.writerow([
                d.id,
                d.donor.name if d.donor else 'Anonymous',
                d.donor.email if d.donor else '',
                d.type,
                d.category,
                d.amount if d.type == 'Monetary' else d.quantity,
                d.unit,
                d.status,
                d.date.strftime('%Y-%m-%d %H:%M'),
                d.block_hash or ''
            ])
        filename = f"donations_report_{datetime.utcnow().strftime('%Y%m%d')}.csv"

    elif report_type == 'distributions':
        writer.writerow(['Distribution ID', 'Beneficiary', 'Location', 'Staff Member', 'Items', 'Date', 'Block Hash'])
        distributions = Distribution.query.order_by(Distribution.date.desc()).all()
        for dist in distributions:
            items_str = "; ".join([f"{item.quantity} {item.inventory_item.name if item.inventory_item else 'item'}" for item in dist.items])
            writer.writerow([
                dist.id,
                dist.beneficiary.name if dist.beneficiary else 'Unknown',
                dist.location,
                dist.staff.name if dist.staff else 'NGO Staff',
                items_str,
                dist.date.strftime('%Y-%m-%d %H:%M'),
                dist.block_hash or ''
            ])
        filename = f"distributions_report_{datetime.utcnow().strftime('%Y%m%d')}.csv"

    elif report_type == 'inventory':
        writer.writerow(['Item ID', 'Category', 'Item Name', 'Quantity', 'Unit', 'Demand', 'Stock Status'])
        items = InventoryItem.query.order_by(InventoryItem.category.asc()).all()
        for item in items:
            writer.writerow([
                item.id,
                item.category,
                item.name,
                item.quantity,
                item.unit,
                item.low_stock_threshold,
                'LOW STOCK' if item.is_low_stock else 'OK'
            ])
        filename = f"inventory_report_{datetime.utcnow().strftime('%Y%m%d')}.csv"

    elif report_type == 'ledger':
        writer.writerow(['Block Index', 'Record Type', 'Record ID', 'Timestamp', 'Previous Hash', 'Block Hash'])
        blocks = LedgerBlock.query.order_by(LedgerBlock.index.asc()).all()
        for b in blocks:
            writer.writerow([
                b.index,
                b.record_type,
                b.record_id,
                b.timestamp,
                b.previous_hash,
                b.block_hash
            ])
        filename = f"ledger_audit_chain_{datetime.utcnow().strftime('%Y%m%d')}.csv"

    else:
        return jsonify({'error': 'Invalid report type'}), 400

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )
