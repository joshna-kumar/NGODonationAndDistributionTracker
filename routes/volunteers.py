from datetime import datetime, timezone
import math

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from database import db
from models.beneficiary import Beneficiary
from models.distribution import Distribution, DistributionItem
from models.donation import Donation
from models.donor import Donor
from models.inventory import InventoryItem, InventoryLog
from models.user import User
from models.volunteer_task import VolunteerLocation, VolunteerTask
from utils.auth import role_required
from utils.blockchain import add_record_to_ledger
from utils.helpers import log_activity

volunteers_bp = Blueprint('volunteers', __name__, url_prefix='/api/volunteer-tasks')


def task_for_request(task_id):
    task = db.session.get(VolunteerTask, task_id)
    if not task:
        return None, (jsonify({'error': 'Volunteer task not found.'}), 404)
    if current_user.role == 'volunteer' and task.volunteer_id != current_user.id:
        return None, (jsonify({'error': 'This task is not assigned to your account.'}), 403)
    if current_user.role == 'donor':
        donor = Donor.query.filter((Donor.user_id == current_user.id) | (Donor.email == current_user.email)).first()
        if not donor or task.donor_id != donor.id:
            return None, (jsonify({'error': 'This task is not associated with your account.'}), 403)
    return task, None


@volunteers_bp.route('/volunteers', methods=['GET'])
@login_required
@role_required('admin', 'staff')
def list_volunteer_accounts():
    users = User.query.filter_by(role='volunteer').order_by(User.name.asc()).all()
    return jsonify({'volunteers': [
        {'id': user.id, 'name': user.name, 'email': user.email, 'phone': user.phone or ''}
        for user in users
    ]})


@volunteers_bp.route('/pending-donations', methods=['GET'])
@login_required
@role_required('admin', 'staff')
def list_pending_goods_donations():
    donations = Donation.query.filter(
        (Donation.type == 'In-Kind') | (Donation.category != 'Money')
    ).order_by(Donation.date.desc()).all()
    pending = []
    for d in donations:
        latest_task = d.volunteer_tasks[-1] if (hasattr(d, 'volunteer_tasks') and d.volunteer_tasks) else None
        if not latest_task or latest_task.status in ('Rejected',):
            pending.append(d.to_dict())
    return jsonify({'pending_donations': pending, 'pending_goods_donations': pending})


@volunteers_bp.route('', methods=['GET'])
@login_required
@role_required('admin', 'staff', 'volunteer', 'donor')
def list_tasks():
    query = VolunteerTask.query
    if current_user.role == 'volunteer':
        query = query.filter_by(volunteer_id=current_user.id)
    elif current_user.role == 'donor':
        donor = Donor.query.filter((Donor.user_id == current_user.id) | (Donor.email == current_user.email)).first()
        if not donor:
            return jsonify({'tasks': []})
        query = query.filter_by(donor_id=donor.id)
    tasks = query.order_by(VolunteerTask.created_at.desc()).all()
    return jsonify({'tasks': [task.to_dict(include_private=True) for task in tasks]})



@volunteers_bp.route('', methods=['POST'])
@login_required
@role_required('staff')
def create_task():
    data = request.get_json(silent=True) or {}
    task_type = str(data.get('task_type') or '').strip().lower()
    if task_type not in ('pickup', 'delivery'):
        return jsonify({'error': 'Task type must be pickup or delivery.'}), 400

    volunteer = db.session.get(User, data.get('volunteer_id'))
    if not volunteer or volunteer.role != 'volunteer':
        return jsonify({'error': 'Choose a valid volunteer account.'}), 400

    try:
        expected_quantity = float(data.get('expected_quantity') or 0)
    except (TypeError, ValueError):
        expected_quantity = 0

    donation_id = data.get('donation_id')
    donation = db.session.get(Donation, donation_id) if donation_id else None

    task = VolunteerTask(
        volunteer_id=volunteer.id,
        task_type=task_type,
        item_name=(data.get('item_name') or '').strip() or None,
        category=(data.get('category') or '').strip() or None,
        unit=(data.get('unit') or 'units').strip(),
        expected_quantity=expected_quantity,
        notes=(data.get('notes') or '').strip()
    )

    if task_type == 'pickup':
        donor_id = data.get('donor_id') or (donation.donor_id if donation else None)
        donor = db.session.get(Donor, donor_id)
        if not donor:
            return jsonify({'error': 'Choose a valid donor for pickup.'}), 400

        if not task.item_name and donation:
            task.item_name = donation.item_name or donation.notes or f"{donation.category} Supplies"
        if not task.category and donation:
            task.category = donation.category
        if (not task.expected_quantity or task.expected_quantity <= 0) and donation:
            task.expected_quantity = donation.quantity
        if (not task.unit or task.unit == 'units') and donation and donation.unit:
            task.unit = donation.unit

        if not donor.address or not task.item_name or not task.category or not math.isfinite(task.expected_quantity) or task.expected_quantity <= 0:
            return jsonify({'error': 'Pickup requires a donor address, item name, category, and positive expected quantity.'}), 400
        task.donor_id = donor.id
        if donation:
            task.donation_id = donation.id
            donation.status = f"Assigned to {volunteer.name}"
    else:
        beneficiary = db.session.get(Beneficiary, data.get('beneficiary_id'))
        item = db.session.get(InventoryItem, data.get('inventory_item_id'))
        if not beneficiary or not item:
            return jsonify({'error': 'Delivery requires a valid beneficiary and inventory item.'}), 400
        if (not math.isfinite(task.expected_quantity) or task.expected_quantity <= 0 or
            item.quantity < task.expected_quantity):
            return jsonify({'error': 'Delivery quantity must be positive and available in inventory.'}), 400
        task.beneficiary_id = beneficiary.id
        task.inventory_item_id = item.id
        task.item_name = item.name
        task.category = item.category
        task.unit = item.unit

    db.session.add(task)
    db.session.commit()
    log_activity('ASSIGN', 'VOLUNTEER_TASK', task.id, f'Assigned {task_type} task to {volunteer.name}')
    return jsonify({'message': 'Volunteer task assigned.', 'task': task.to_dict(include_private=True)}), 201


@volunteers_bp.route('/<int:task_id>', methods=['GET'])
@login_required
@role_required('admin', 'staff', 'volunteer', 'donor', 'auditor')
def get_task(task_id):
    task, error = task_for_request(task_id)
    if error:
        return error
    return jsonify({'task': task.to_dict(include_private=True)})


@volunteers_bp.route('/<int:task_id>/location', methods=['GET'])
@login_required
@role_required('admin', 'staff', 'volunteer', 'donor', 'auditor')
def get_task_location(task_id):
    task, error = task_for_request(task_id)
    if error:
        return error
    latest_location = task.locations[-1] if task.locations else None
    return jsonify({
        'task_id': task.id,
        'location_sharing': task.location_sharing,
        'latest_location': latest_location.to_dict() if latest_location else None,
        'location_history': [location.to_dict() for location in task.locations]
    })


@volunteers_bp.route('/<int:task_id>/location', methods=['POST'])
@login_required
@role_required('admin', 'staff', 'volunteer')
def update_task_location(task_id):
    task, error = task_for_request(task_id)
    if error:
        return error
    if current_user.role != 'volunteer':
        return jsonify({'error': 'Only the assigned volunteer can share GPS location.'}), 403
    if task.status in ('Completed', 'Returned', 'Sent to Inventory', 'Delivered'):
        return jsonify({'error': 'Completed tasks cannot share location.'}), 409

    data = request.get_json(silent=True) or {}
    action = data.get('action')
    if action == 'stop':
        task.location_sharing = False
        db.session.commit()
        return jsonify({'message': 'Location sharing stopped.', 'task': task.to_dict(include_private=True)})

    if action not in ('start', 'update'):
        return jsonify({'error': 'Action must be start, update, or stop.'}), 400
    if action == 'start' and task.status == 'Assigned':
        return jsonify({'error': 'Accept the task before starting GPS tracking.'}), 409
    if action == 'update' and not task.location_sharing:
        return jsonify({'error': 'Start task location sharing before sending GPS updates.'}), 409

    try:
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))
        accuracy = float(data.get('accuracy_meters')) if data.get('accuracy_meters') is not None else None
    except (TypeError, ValueError):
        return jsonify({'error': 'Valid GPS coordinates are required.'}), 400
    if not math.isfinite(latitude) or not math.isfinite(longitude) or not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return jsonify({'error': 'GPS coordinates are out of range.'}), 400
    if accuracy is not None and (not math.isfinite(accuracy) or accuracy < 0):
        return jsonify({'error': 'GPS accuracy must be a non-negative number.'}), 400

    if action == 'start':
        task.location_sharing = True
    db.session.add(VolunteerLocation(
        task_id=task.id,
        latitude=latitude,
        longitude=longitude,
        accuracy_meters=accuracy
    ))
    db.session.commit()
    log_activity('LOCATION', 'VOLUNTEER_TASK', task.id, f'Volunteer location {action}ed for task #{task.id}')
    return jsonify({'message': 'Task location updated.', 'task': task.to_dict(include_private=True)})


@volunteers_bp.route('/<int:task_id>/status', methods=['POST'])
@login_required
@role_required('volunteer')
def update_task_status(task_id):
    task, error = task_for_request(task_id)
    if error:
        return error
    if task.status in ('Completed', 'Returned', 'Sent to Inventory', 'Delivered'):
        return jsonify({'error': 'This task is already complete.'}), 409

    data = request.get_json(silent=True) or {}
    next_status = str(data.get('status') or '').strip()
    transitions = {
        'Assigned': {'Accepted', 'Rejected'},
        'Accepted': {'On the Way', 'At Donor\'s Location'} if task.task_type == 'pickup' else {'Out for Delivery'},
        'On the Way': {'At Donor\'s Location', 'Picked Up'},
        'At Donor\'s Location': {'Picked Up'},
        'Picked Up': {'Returned', 'Sent to Inventory'},
        'Out for Delivery': {'Delivered'},
        'In Progress': {'On the Way', 'At Donor\'s Location'} if task.task_type == 'pickup' else {'Out for Delivery'}
    }
    if next_status not in transitions.get(task.status, set()):
        return jsonify({'error': f'Invalid next status for a {task.task_type} task.'}), 409

    if next_status == 'Rejected':
        old_status = task.status
        task.status = 'Rejected'
        task.location_sharing = False
        task.volunteer_id = None
        if task.donation:
            task.donation.status = 'Pending Pickup'
        db.session.commit()
        log_activity('REJECT', 'VOLUNTEER_TASK', task.id, f'Volunteer rejected task #{task.id}')
        return jsonify({'message': 'Task rejected and returned to staff.', 'task': task.to_dict(include_private=True)})

    if next_status in ('Returned', 'Sent to Inventory', 'Delivered'):
        try:
            quantity = float(data.get('quantity') or 0)
        except (TypeError, ValueError):
            quantity = 0
        if not math.isfinite(quantity) or quantity <= 0:
            return jsonify({'error': 'Enter the positive quantity collected or delivered.'}), 400
        return complete_task_records(task, quantity, final_status=next_status)

    old_status = task.status
    task.status = next_status
    if task.donation:
        status_map = {
            'Accepted': 'Pickup Accepted',
            'On the Way': 'Volunteer On The Way',
            'At Donor\'s Location': 'Volunteer At Donor Location',
            'Picked Up': 'Goods Picked Up'
        }
        if next_status in status_map:
            task.donation.status = status_map[next_status]

    db.session.commit()
    log_activity('STATUS', 'VOLUNTEER_TASK', task.id, f'Volunteer {current_user.name} updated task from {old_status} to {next_status}')
    return jsonify({'message': f'Task status updated to {next_status}.', 'task': task.to_dict(include_private=True)})


@volunteers_bp.route('/<int:task_id>/complete', methods=['POST'])
@login_required
@role_required('volunteer')
def complete_task(task_id):
    task, error = task_for_request(task_id)
    if error:
        return error
    required_status = 'Picked Up' if task.task_type == 'pickup' else 'Out for Delivery'
    if task.status != required_status:
        return jsonify({'error': f'Update this task to {required_status} before completing it.'}), 409

    data = request.get_json(silent=True) or {}
    try:
        quantity = float(data.get('quantity') or 0)
    except (TypeError, ValueError):
        quantity = 0
    if not math.isfinite(quantity) or quantity <= 0:
        return jsonify({'error': 'Enter the positive quantity collected or delivered.'}), 400
    return complete_task_records(task, quantity)


def complete_task_records(task, quantity, final_status=None):
    if task.task_type == 'pickup':
        category = task.category or 'General'
        item_name = task.item_name or f'{category} Supplies'
        if task.donation_id and task.donation:
            donation = task.donation
            donation.quantity = quantity
            donation.status = 'Received in Inventory'
            donation.notes = f"{donation.notes or ''} Collected by volunteer {current_user.name} and delivered to inventory.".strip()
        else:
            donation = Donation(
                donor_id=task.donor_id,
                type='In-Kind',
                category=category,
                amount=0,
                quantity=quantity,
                unit=task.unit or 'units',
                status='Received in Inventory',
                notes=f'Collected by volunteer {current_user.name}. {task.notes or ""}'.strip()
            )
            db.session.add(donation)
            db.session.flush()
            task.donation_id = donation.id

        item = InventoryItem.query.filter_by(name=item_name, category=category).first()
        if not item:
            item = InventoryItem(
                name=item_name,
                category=category,
                quantity=quantity,
                unit=task.unit or 'units',
                low_stock_threshold=10
            )
            db.session.add(item)
            db.session.flush()
        else:
            item.quantity += quantity

        db.session.add(InventoryLog(
            inventory_item_id=item.id,
            movement_type='INBOUND',
            quantity=quantity,
            reference_type='DONATION',
            reference_id=donation.id,
            notes=f'Volunteer pickup task #{task.id} completed.'
        ))
        ledger_payload = {
            'donation_id': donation.id,
            'donor_name': task.donor.name if task.donor else 'Donor',
            'type': 'In-Kind',
            'category': category,
            'value': f'{quantity} {task.unit or "units"} of {item_name}',
            'status': 'Received in Inventory',
            'logged_by': current_user.name,
            'volunteer_task_id': task.id
        }
        block = add_record_to_ledger('DONATION', donation.id, ledger_payload)
        donation.block_hash = block.block_hash
    else:
        if quantity > task.expected_quantity:
            return jsonify({'error': 'Delivered quantity cannot exceed the amount assigned for this task.'}), 400
        item = db.session.get(InventoryItem, task.inventory_item_id)
        if not item or item.quantity < quantity:
            return jsonify({'error': 'Not enough stock remains to complete this delivery.'}), 409
        distribution = Distribution(
            beneficiary_id=task.beneficiary_id,
            staff_id=current_user.id,
            location=task.beneficiary.location,
            notes=f'Delivered by volunteer {current_user.name}. {task.notes or ""}'.strip(),
            status='Completed'
        )
        db.session.add(distribution)
        db.session.flush()
        db.session.add(DistributionItem(
            distribution_id=distribution.id,
            inventory_item_id=item.id,
            quantity=quantity
        ))
        item.quantity -= quantity
        db.session.add(InventoryLog(
            inventory_item_id=item.id,
            movement_type='OUTBOUND',
            quantity=quantity,
            reference_type='DISTRIBUTION',
            reference_id=distribution.id,
            notes=f'Volunteer delivery task #{task.id} completed.'
        ))
        block = add_record_to_ledger('DISTRIBUTION', distribution.id, {
            'distribution_id': distribution.id,
            'beneficiary_id': task.beneficiary_id,
            'items': f'{quantity} {item.unit} of {item.name}',
            'volunteer_task_id': task.id,
            'logged_by': current_user.name
        })
        distribution.block_hash = block.block_hash

    task.status = final_status or ('Returned' if task.task_type == 'pickup' else 'Delivered')
    task.location_sharing = False
    task.completed_at = datetime.now(timezone.utc)
    db.session.commit()
    log_activity('COMPLETE', 'VOLUNTEER_TASK', task.id, f'Completed {task.task_type} task #{task.id}')
    return jsonify({'message': 'Task completed and records updated.', 'task': task.to_dict(include_private=True)})

