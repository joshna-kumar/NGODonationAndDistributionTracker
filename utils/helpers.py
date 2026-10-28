from database import db
from models.audit import ActivityLog
from models.donor import Donor
from flask_login import current_user
import re

def log_activity(action, entity, entity_id=None, details=None):
    """
    Utility to record an administrative activity log entry.
    """
    try:
        user_id = current_user.id if current_user and current_user.is_authenticated else None
        user_name = current_user.name if current_user and current_user.is_authenticated else 'System/Public'
        user_role = current_user.role if current_user and current_user.is_authenticated else 'Public'

        log_entry = ActivityLog(
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            action=action,
            entity=entity,
            entity_id=entity_id,
            details=details or ''
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        print(f"Error logging activity: {e}")

def normalize_string(s):
    if not s:
        return ""
    return re.sub(r'[^a-z0-9]', '', str(s).lower())

def find_duplicate_donors(name="", email="", phone="", exclude_id=None):
    """
    Fuzzy match logic to detect duplicate donors by email, phone, or normalized name similarity.
    """
    donors = Donor.query.all()
    duplicates = []

    norm_name = normalize_string(name)
    norm_email = normalize_string(email)
    norm_phone = normalize_string(phone)

    for donor in donors:
        if exclude_id and donor.id == exclude_id:
            continue

        match_reasons = []
        d_name = normalize_string(donor.name)
        d_email = normalize_string(donor.email)
        d_phone = normalize_string(donor.phone)

        if norm_email and norm_email == d_email:
            match_reasons.append("Exact Email Match")

        if norm_phone and norm_phone == d_phone:
            match_reasons.append("Exact Phone Match")

        if norm_name and norm_name == d_name:
            match_reasons.append("Exact Name Match")
        elif norm_name and d_name and (norm_name in d_name or d_name in norm_name) and len(norm_name) >= 4:
            match_reasons.append("Partial Name Match")

        if match_reasons:
            duplicates.append({
                'donor': donor.to_dict(),
                'reasons': match_reasons
            })

    return duplicates

def generate_donation_receipt_data(donation):
    """
    Generates structured receipt metadata tied to the donation's block hash.
    """
    return {
        'receipt_number': f"REC-{donation.id:06d}",
        'donation_id': donation.id,
        'donor_name': donation.donor.name if donation.donor else 'Anonymous',
        'donor_email': donation.donor.email if donation.donor else '',
        'donor_address': donation.donor.address if donation.donor else '',
        'donation_type': donation.type,
        'category': donation.category,
        'amount': donation.amount if donation.type == 'Monetary' else donation.quantity,
        'unit': donation.unit,
        'date': donation.date.strftime('%B %d, %Y %H:%M UTC') if donation.date else '',
        'status': donation.status,
        'block_hash': donation.block_hash or 'UNVERIFIED',
        'issued_by': 'Global NGO Alliance & Distribution Network',
        'verification_notice': 'This receipt is immutably recorded in the NGO SHA-256 Blockchain Ledger.'
    }
