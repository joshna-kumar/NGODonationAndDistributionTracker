from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from database import db
from models.inventory import InventoryItem, InventoryLog
from utils.auth import role_required
from utils.helpers import log_activity

inventory_bp = Blueprint('inventory', __name__, url_prefix='/api/inventory')

@inventory_bp.route('', methods=['GET'])
@login_required
@role_required('admin', 'staff', 'auditor')
def list_inventory():
    category = request.args.get('category', '').strip()
    low_stock_only = request.args.get('low_stock', '').lower() == 'true'
    search = request.args.get('search', '').strip()

    query = InventoryItem.query

    if category:
        query = query.filter(InventoryItem.category == category)

    if search:
        query = query.filter(
            (InventoryItem.name.ilike(f'%{search}%')) |
            (InventoryItem.category.ilike(f'%{search}%'))
        )

    items = query.order_by(InventoryItem.name.asc()).all()

    if low_stock_only:
        items = [i for i in items if i.is_low_stock]

    return jsonify({
        'inventory': [i.to_dict() for i in items],
        'low_stock_count': sum(1 for i in items if i.is_low_stock)
    })

@inventory_bp.route('/<int:item_id>', methods=['GET'])
@login_required
@role_required('admin', 'staff', 'auditor')
def get_inventory_item(item_id):
    item = InventoryItem.query.get_or_404(item_id)
    item_dict = item.to_dict()
    item_dict['movement_logs'] = [l.to_dict() for l in item.logs[-20:]]
    return jsonify({'inventory_item': item_dict})

@inventory_bp.route('', methods=['POST'])
@login_required
@role_required('admin', 'staff')
def create_inventory_item():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    category = data.get('category', 'General').strip()
    quantity = float(data.get('quantity') or 0.0)
    unit = data.get('unit', 'units').strip()
    low_stock_threshold = float(data.get('low_stock_threshold') or 10.0)

    if not name or not category:
        return jsonify({'error': 'Name and category are required.'}), 400

    existing = InventoryItem.query.filter_by(name=name, category=category).first()
    if existing:
        return jsonify({'error': f'Inventory item "{name}" already exists in category "{category}". Use update to adjust stock.'}), 400

    item = InventoryItem(
        name=name,
        category=category,
        quantity=quantity,
        unit=unit,
        low_stock_threshold=low_stock_threshold
    )
    db.session.add(item)
    db.session.flush()

    # Log initial stock
    if quantity > 0:
        inv_log = InventoryLog(
            inventory_item_id=item.id,
            movement_type='INBOUND',
            quantity=quantity,
            reference_type='MANUAL',
            notes='Initial stock creation'
        )
        db.session.add(inv_log)

    db.session.commit()
    log_activity('CREATE', 'INVENTORY', item.id, f'Created inventory item {name} with stock {quantity} {unit}')

    return jsonify({
        'message': 'Inventory item added successfully',
        'inventory_item': item.to_dict()
    }), 201

@inventory_bp.route('/<int:item_id>', methods=['PUT'])
@login_required
@role_required('admin', 'staff')
def update_inventory_item(item_id):
    item = InventoryItem.query.get_or_404(item_id)
    data = request.get_json() or {}

    old_qty = item.quantity
    item.name = data.get('name', item.name).strip()
    item.category = data.get('category', item.category).strip()
    item.unit = data.get('unit', item.unit).strip()
    item.low_stock_threshold = float(data.get('low_stock_threshold', item.low_stock_threshold))

    new_qty = data.get('quantity')
    if new_qty is not None:
        new_qty = float(new_qty)
        diff = new_qty - old_qty
        if diff != 0:
            item.quantity = new_qty
            inv_log = InventoryLog(
                inventory_item_id=item.id,
                movement_type='ADJUSTMENT' if diff > 0 else 'OUTBOUND',
                quantity=abs(diff),
                reference_type='MANUAL',
                notes=f'Manual stock adjustment from {old_qty} to {new_qty} by {current_user.name}'
            )
            db.session.add(inv_log)

    db.session.commit()
    log_activity('UPDATE', 'INVENTORY', item.id, f'Updated inventory item {item.name}')

    return jsonify({
        'message': 'Inventory item updated successfully',
        'inventory_item': item.to_dict()
    })

@inventory_bp.route('/movement-logs', methods=['GET'])
@login_required
@role_required('admin', 'staff', 'auditor')
def get_movement_logs():
    item_id = request.args.get('item_id')
    query = InventoryLog.query

    if item_id:
        query = query.filter_by(inventory_item_id=int(item_id))

    logs = query.order_by(InventoryLog.timestamp.desc()).limit(100).all()
    return jsonify({'logs': [l.to_dict() for l in logs]})
