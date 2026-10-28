import os
import uuid
from decimal import Decimal, InvalidOperation

import requests
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from database import db
from models.donation import Donation
from models.donor import Donor
from models.cashfree_order import CashfreeOrder
from models.inventory import InventoryItem, InventoryLog
from utils.auth import role_required
from utils.blockchain import add_record_to_ledger
from utils.helpers import log_activity, generate_donation_receipt_data

donations_bp = Blueprint('donations', __name__, url_prefix='/api/donations')
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}


def cashfree_api_url():
    environment = current_app.config.get('CASHFREE_ENVIRONMENT', 'sandbox')
    host = 'https://api.cashfree.com/pg' if environment == 'production' else 'https://sandbox.cashfree.com/pg'
    return host


def cashfree_headers(idempotency_key=None):
    headers = {
        'x-api-version': '2023-08-01',
        'x-client-id': current_app.config.get('CASHFREE_APP_ID', ''),
        'x-client-secret': current_app.config.get('CASHFREE_SECRET_KEY', ''),
        'Content-Type': 'application/json'
    }
    if idempotency_key:
        headers['x-idempotency-key'] = idempotency_key
    return headers


def cashfree_is_configured():
    return bool(
        current_app.config.get('CASHFREE_APP_ID') and
        current_app.config.get('CASHFREE_SECRET_KEY')
    )


def save_donation_image(upload, prefix):
    if not upload or not upload.filename:
        return None
    extension = upload.filename.rsplit('.', 1)[-1].lower() if '.' in upload.filename else ''
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError('Only JPG, PNG, and WEBP images are allowed.')

    upload_directory = os.path.join(current_app.static_folder, 'uploads')
    os.makedirs(upload_directory, exist_ok=True)
    filename = f'{prefix}-{uuid.uuid4().hex}.{extension}'
    upload.save(os.path.join(upload_directory, secure_filename(filename)))
    return f'uploads/{filename}'

@donations_bp.route('', methods=['GET'])
@login_required
@role_required('admin', 'staff', 'donor', 'auditor')
def list_donations():
    # If Donor role, only show own donations!
    query = Donation.query

    if current_user.role == 'donor':
        donor = Donor.query.filter_by(user_id=current_user.id).first()
        if not donor:
            donor = Donor.query.filter_by(email=current_user.email).first()
        if donor:
            query = query.filter_by(donor_id=donor.id)
        else:
            return jsonify({'donations': []})

    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    donation_type = request.args.get('type', '').strip()

    if search:
        query = query.join(Donor).filter(
            (Donor.name.ilike(f'%{search}%')) |
            (Donation.category.ilike(f'%{search}%')) |
            (Donation.notes.ilike(f'%{search}%'))
        )

    if category:
        query = query.filter(Donation.category == category)

    if donation_type:
        query = query.filter(Donation.type == donation_type)

    donations = query.order_by(Donation.date.desc()).all()
    return jsonify({'donations': [d.to_dict() for d in donations]})

@donations_bp.route('/<int:donation_id>', methods=['GET'])
@login_required
@role_required('admin', 'staff', 'donor', 'auditor')
def get_donation(donation_id):
    donation = Donation.query.get_or_404(donation_id)

    if current_user.role == 'donor':
        if not donation.donor or (donation.donor.user_id != current_user.id and donation.donor.email != current_user.email):
            return jsonify({'error': 'Unauthorized to view this donation'}), 403

    return jsonify({'donation': donation.to_dict()})

@donations_bp.route('/cashfree/config', methods=['GET'])
def cashfree_config():
    return jsonify({
        'enabled': cashfree_is_configured(),
        'environment': current_app.config.get('CASHFREE_ENVIRONMENT', 'sandbox')
    })


@donations_bp.route('/cashfree/create-order', methods=['POST'])
@login_required
def create_cashfree_order():
    if current_user.role not in ('admin', 'staff', 'donor'):
        return jsonify({'error': 'You do not have permission to pay for donations.'}), 403

    if not cashfree_is_configured():
        return jsonify({'error': 'Cashfree is not configured. Set CASHFREE_APP_ID and CASHFREE_SECRET_KEY.'}), 503

    payload = request.get_json(silent=True) or {}
    try:
        amount = Decimal(str(payload.get('amount') or '0')).quantize(Decimal('0.01'))
    except InvalidOperation:
        amount = Decimal('0')
    if amount <= 0:
        return jsonify({'error': 'Donation amount must be greater than zero.'}), 400

    donor_id = payload.get('donor_id')
    if current_user.role == 'donor':
        donor = Donor.query.filter_by(user_id=current_user.id).first()
        if not donor:
            donor = Donor.query.filter_by(email=current_user.email).first()
        if not donor:
            donor = Donor(user_id=current_user.id, name=current_user.name, email=current_user.email)
            db.session.add(donor)
            db.session.flush()
    else:
        donor = Donor.query.get(donor_id) if donor_id else None
        if not donor:
            return jsonify({'error': 'Select a valid donor before creating the payment.'}), 400

    raw_phone = (payload.get('customer_phone') or donor.phone or current_user.phone or '').strip()
    customer_phone = ''.join(character for character in raw_phone if character.isdigit())
    if len(customer_phone) < 10 or len(customer_phone) > 15:
        return jsonify({'error': 'Enter a valid donor phone number for Cashfree checkout.'}), 400

    public_base_url = current_app.config.get('PUBLIC_BASE_URL', '').rstrip('/')
    if not public_base_url:
        return jsonify({'error': 'Set PUBLIC_BASE_URL to the public HTTPS website URL before creating Cashfree orders.'}), 503

    order_id = f'ngo_{uuid.uuid4().hex[:28]}'
    order = CashfreeOrder(
        order_id=order_id,
        donor_id=donor.id,
        amount=amount,
        category=(payload.get('category') or 'Money')[:80],
        notes=(payload.get('notes') or '').strip()
    )
    db.session.add(order)

    try:
        response = requests.post(
            f'{cashfree_api_url()}/orders',
            headers=cashfree_headers(uuid.uuid4().hex),
            json={
                'order_id': order_id,
                'order_amount': float(amount),
                'order_currency': 'INR',
                'customer_details': {
                    'customer_id': f'ngo-user-{current_user.id}',
                    'customer_name': donor.name[:100],
                    'customer_email': donor.email,
                    'customer_phone': customer_phone
                },
                'order_meta': {
                    'return_url': f'{public_base_url}/?cashfree_order_id={{order_id}}'
                },
                'order_note': 'NGO donation'
            },
            timeout=20
        )
        response.raise_for_status()
        cashfree_response = response.json()
        if not cashfree_response.get('payment_session_id'):
            raise ValueError('Cashfree response did not include a payment session.')
    except (requests.RequestException, ValueError):
        db.session.rollback()
        current_app.logger.exception('Cashfree order creation failed')
        return jsonify({'error': 'Cashfree could not create the payment order. Check the Cashfree credentials and try again.'}), 502

    db.session.commit()
    return jsonify({
        'order_id': order_id,
        'payment_session_id': cashfree_response.get('payment_session_id'),
        'environment': current_app.config.get('CASHFREE_ENVIRONMENT', 'sandbox')
    }), 201


@donations_bp.route('/cashfree/confirm', methods=['POST'])
@login_required
def confirm_cashfree_order():
    payload = request.get_json(silent=True) or {}
    order_id = str(payload.get('order_id', '')).strip()
    order = CashfreeOrder.query.get(order_id)
    if not order:
        return jsonify({'error': 'Cashfree order was not found.'}), 404

    if current_user.role == 'donor' and order.donor.user_id != current_user.id and order.donor.email != current_user.email:
        return jsonify({'error': 'Unauthorized to confirm this donation.'}), 403

    if order.donation_id:
        return jsonify({'message': 'Donation already recorded.', 'donation_id': order.donation_id})

    if not cashfree_is_configured():
        return jsonify({'error': 'Cashfree is not configured.'}), 503

    try:
        response = requests.get(
            f'{cashfree_api_url()}/orders/{order.order_id}',
            headers=cashfree_headers(),
            timeout=20
        )
        response.raise_for_status()
        payment_order = response.json()
    except (requests.RequestException, ValueError):
        current_app.logger.exception('Cashfree order confirmation failed')
        return jsonify({'error': 'Could not confirm payment with Cashfree. Please retry.'}), 502

    try:
        paid_amount = Decimal(str(payment_order.get('order_amount'))).quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError):
        paid_amount = Decimal('0')

    if (payment_order.get('order_status') != 'PAID' or
            payment_order.get('order_currency') != 'INR' or
            paid_amount != order.amount):
        return jsonify({'error': 'Cashfree has not confirmed payment for the expected amount.'}), 409

    donation = Donation(
        donor_id=order.donor_id,
        type='Monetary',
        category=order.category,
        amount=float(order.amount),
        quantity=0,
        unit='INR',
        status='Verified',
        notes=order.notes
    )
    db.session.add(donation)
    db.session.flush()
    order.donor.total_donated = (order.donor.total_donated or 0.0) + float(order.amount)
    ledger_payload = {
        'donation_id': donation.id,
        'donor_name': order.donor.name,
        'donor_email': order.donor.email,
        'type': 'Monetary',
        'category': order.category,
        'value': f'{order.amount} INR',
        'status': 'Verified',
        'payment_gateway': 'Cashfree',
        'payment_order_id': order.order_id,
        'logged_by': current_user.name
    }
    block = add_record_to_ledger('DONATION', donation.id, ledger_payload)
    donation.block_hash = block.block_hash
    order.status = 'PAID'
    order.donation_id = donation.id
    db.session.commit()

    log_activity('CREATE', 'DONATION', donation.id, f'Cashfree payment confirmed for donation from {order.donor.name} (Block #{block.index})')

    return jsonify({
        'message': 'Cashfree payment confirmed and donation recorded.',
        'donation': donation.to_dict(),
        'receipt': generate_donation_receipt_data(donation)
    })


@donations_bp.route('', methods=['POST'])
@login_required
def create_donation():
    data = request.form if request.form else (request.get_json() or {})

    if current_user.role != 'donor':
        return jsonify({'error': 'You do not have permission to record donations.'}), 403

    donor_id = data.get('donor_id')
    
    # If current user is a donor, associate automatically
    if current_user.role == 'donor':
        donor = Donor.query.filter_by(user_id=current_user.id).first()
        if not donor:
            donor = Donor.query.filter_by(email=current_user.email).first()
        if not donor:
            donor = Donor(user_id=current_user.id, name=current_user.name, email=current_user.email)
            db.session.add(donor)
            db.session.commit()
        donor_id = donor.id

    if not donor_id:
        return jsonify({'error': 'Donor selection is required.'}), 400

    donor = Donor.query.get(donor_id)
    if not donor:
        return jsonify({'error': 'Selected donor does not exist.'}), 404

    # Update donor phone and address if supplied
    donor_phone_input = (data.get('donor_phone') or data.get('phone') or '').strip()
    if donor_phone_input:
        donor.phone = donor_phone_input
        if current_user.is_authenticated and current_user.role == 'donor':
            current_user.phone = donor_phone_input

    donor_address_input = (data.get('donor_address') or data.get('address') or '').strip()
    if donor_address_input:
        donor.address = donor_address_input

    category = data.get('category', 'Money')
    donation_type = data.get('type')
    if not donation_type:
        donation_type = 'Monetary' if category == 'Money' else 'In-Kind'

    amount = float(data.get('amount') or 0.0)
    quantity = float(data.get('quantity') or 0.0)
    unit = data.get('unit', 'INR' if donation_type == 'Monetary' else 'units')

    notes = data.get('notes', '').strip()
    item_name = data.get('item_name', '').strip()
    payment_method = str(data.get('payment_method', '')).lower()
    is_gpay = payment_method in ('gpay', 'upi') or data.get('status') == 'Payment Successful'
    product_photo = request.files.get('product_photo') if request.files else None
    payment_screenshot = request.files.get('payment_screenshot') if request.files else None

    if donation_type == 'Monetary' and amount <= 0:
        return jsonify({'error': 'Monetary donation amount must be greater than 0.'}), 400

    if donation_type == 'In-Kind' and quantity <= 0:
        return jsonify({'error': 'In-kind donation quantity must be greater than 0.'}), 400
    if donation_type == 'Monetary' and not payment_screenshot and not is_gpay:
        return jsonify({'error': 'Upload a payment screenshot for a manual monetary donation.'}), 400

    product_photo_path = None
    payment_screenshot_path = None
    try:
        if product_photo and product_photo.filename:
            product_photo_path = save_donation_image(product_photo, 'product')
        if payment_screenshot and payment_screenshot.filename:
            payment_screenshot_path = save_donation_image(payment_screenshot, 'payment')
    except ValueError as error:
        return jsonify({'error': str(error)}), 400

    # 1. Create Donation Record
    if donation_type == 'In-Kind' or category != 'Money':
        donation_status = 'Pending Pickup'
    else:
        donation_status = 'Payment Successful' if is_gpay or data.get('status') == 'Payment Successful' else 'Verified'
    evidence_status = 'Valid' if is_gpay else 'Pending Review'

    donation = Donation(
        donor_id=donor.id,
        type=donation_type,
        category=category,
        amount=amount if donation_type == 'Monetary' else 0.0,
        quantity=quantity if donation_type == 'In-Kind' else 0.0,
        unit=unit,
        item_name=item_name or None,
        status=donation_status,
        notes=notes,
        product_photo=product_photo_path,
        payment_screenshot=payment_screenshot_path,
        evidence_status=evidence_status,
        evidence_reviewed_by='Google Pay UPI' if is_gpay else None
    )
    db.session.add(donation)
    db.session.flush() # get ID

    # 2. Update Donor Totals
    if donation_type == 'Monetary':
        donor.total_donated = (donor.total_donated or 0.0) + amount

    # 3. Handle In-Kind Inventory Stock Inbound (if received immediately by staff)
    if donation_type == 'In-Kind' and data.get('received_in_person'):
        name_to_use = item_name or f"{category} Supplies"
        inv_item = InventoryItem.query.filter_by(name=name_to_use, category=category).first()
        if not inv_item:
            inv_item = InventoryItem(
                category=category,
                name=name_to_use,
                quantity=quantity,
                unit=unit,
                low_stock_threshold=10.0
            )
            db.session.add(inv_item)
            db.session.flush()
        else:
            inv_item.quantity += quantity

        inv_log = InventoryLog(
            inventory_item_id=inv_item.id,
            movement_type='INBOUND',
            quantity=quantity,
            reference_type='DONATION',
            reference_id=donation.id,
            notes=f"In-kind donation received from {donor.name}"
        )
        db.session.add(inv_log)

    # 4. Write Blockchain Ledger Block
    ledger_payload = {
        'donation_id': donation.id,
        'donor_name': donor.name,
        'donor_email': donor.email,
        'type': donation_type,
        'category': category,
        'value': f"{amount} {unit}" if donation_type == 'Monetary' else f"{quantity} {unit} of {item_name or category}",
        'status': 'Verified',
        'logged_by': current_user.name
    }
    block = add_record_to_ledger('DONATION', donation.id, ledger_payload)
    donation.block_hash = block.block_hash

    db.session.commit()

    log_activity('CREATE', 'DONATION', donation.id, f'Logged {donation_type} donation of {category} from {donor.name} (Block #{block.index})')

    return jsonify({
        'message': 'Donation recorded and immutably sealed in blockchain ledger!',
        'donation': donation.to_dict(),
        'block_index': block.index,
        'block_hash': block.block_hash,
        'receipt': generate_donation_receipt_data(donation)
    }), 201

@donations_bp.route('/<int:donation_id>/status', methods=['PUT'])
@login_required
@role_required('admin', 'staff')
def update_donation_status(donation_id):
    donation = Donation.query.get_or_404(donation_id)
    data = request.get_json() or {}
    new_status = data.get('status')

    valid_statuses = ['Received', 'Verified', 'Allocated', 'Distributed', 'Payment Successful']
    if new_status not in valid_statuses:
        return jsonify({'error': f'Invalid status. Allowed: {", ".join(valid_statuses)}'}), 400

    old_status = donation.status
    donation.status = new_status
    db.session.commit()

    log_activity('UPDATE', 'DONATION', donation.id, f'Changed donation #{donation.id} status from {old_status} to {new_status}')

    return jsonify({'message': 'Donation status updated', 'donation': donation.to_dict()})


@donations_bp.route('/<int:donation_id>/evidence-status', methods=['PUT'])
@login_required
@role_required('admin')
def update_evidence_status(donation_id):
    donation = Donation.query.get_or_404(donation_id)
    data = request.get_json() or {}
    evidence_status = data.get('evidence_status')

    if evidence_status not in ('Valid', 'Tampered'):
        return jsonify({'error': 'Evidence status must be Valid or Tampered.'}), 400

    donation.evidence_status = evidence_status
    donation.evidence_reviewed_by = current_user.name
    db.session.commit()
    log_activity('REVIEW', 'DONATION', donation.id, f'Marked donation evidence as {evidence_status}')

    return jsonify({'message': f'Donation evidence marked {evidence_status}.', 'donation': donation.to_dict()})

@donations_bp.route('/<int:donation_id>/receipt', methods=['GET'])
@login_required
@role_required('admin', 'staff', 'donor', 'auditor')
def get_donation_receipt(donation_id):
    donation = Donation.query.get_or_404(donation_id)

    if current_user.role == 'donor':
        if not donation.donor or (donation.donor.user_id != current_user.id and donation.donor.email != current_user.email):
            return jsonify({'error': 'Unauthorized'}), 403

    receipt = generate_donation_receipt_data(donation)
    return jsonify({'receipt': receipt})


@donations_bp.route('/gpay-checkout', methods=['POST'])
def gpay_checkout():
    data = request.get_json(silent=True) or request.form or {}
    try:
        amount = float(data.get('amount') or 0.0)
    except (ValueError, TypeError):
        amount = 0.0

    if amount <= 0:
        return jsonify({'error': 'A valid donation amount greater than ₹0 is required.'}), 400

    donor_id = data.get('donor_id')
    donor = None

    if current_user.is_authenticated:
        if current_user.role == 'donor':
            donor = Donor.query.filter_by(user_id=current_user.id).first()
            if not donor:
                donor = Donor.query.filter_by(email=current_user.email).first()
        elif donor_id:
            try:
                donor = Donor.query.get(int(donor_id))
            except (ValueError, TypeError):
                donor = None

    if not donor and donor_id:
        try:
            donor = Donor.query.get(int(donor_id))
        except (ValueError, TypeError):
            donor = None

    if not donor:
        donor = Donor.query.first()
        if not donor:
            donor = Donor(name='GPay Contributor', email='gpay.donor@example.com', preferred_causes='General Support')
            db.session.add(donor)
            db.session.commit()

    notes = data.get('notes', '').strip() or 'Donation completed via Google Pay UPI'

    # Create donation record with status = 'Payment Successful'
    donation = Donation(
        donor_id=donor.id,
        type='Monetary',
        category='Money',
        amount=amount,
        quantity=0.0,
        unit='INR',
        status='Payment Successful',
        notes=notes,
        evidence_status='Valid',
        evidence_reviewed_by='Google Pay UPI'
    )
    db.session.add(donation)
    db.session.flush()

    # Update donor totals
    donor.total_donated = (donor.total_donated or 0.0) + amount

    # Seal in blockchain ledger
    ledger_payload = {
        'donation_id': donation.id,
        'donor_name': donor.name,
        'donor_email': donor.email,
        'type': 'Monetary',
        'category': 'Money',
        'value': f"{amount:.2f} INR",
        'status': 'Payment Successful',
        'gateway': 'Google Pay UPI',
        'logged_by': current_user.name if current_user.is_authenticated else 'Google Pay Gateway'
    }
    block = add_record_to_ledger('DONATION', donation.id, ledger_payload)
    donation.block_hash = block.block_hash

    db.session.commit()

    log_activity('CREATE', 'DONATION', donation.id, f'GPay payment successful: ₹{amount:.2f} from {donor.name} (Block #{block.index})')

    return jsonify({
        'message': 'Payment Successful',
        'status': 'Payment Successful',
        'donation': donation.to_dict(),
        'block_index': block.index,
        'block_hash': block.block_hash,
        'receipt': generate_donation_receipt_data(donation)
    }), 201

