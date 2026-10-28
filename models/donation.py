from datetime import datetime
from database import db

class Donation(db.Model):
    __tablename__ = 'donations'

    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey('donors.id'), nullable=False)
    type = db.Column(db.String(30), nullable=False) # 'Monetary', 'In-Kind'
    category = db.Column(db.String(80), nullable=False) # 'General Fund', 'Food Supplies', 'Medical', 'Education Supplies', 'Clothing'
    amount = db.Column(db.Float, default=0.0) # Monetary amount
    quantity = db.Column(db.Float, default=0.0) # In-kind quantity
    unit = db.Column(db.String(30), default='INR') # INR, kg, boxes, kits, items

    item_name = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(30), default='Received') # Received -> Verified -> Allocated -> Distributed
    date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    block_hash = db.Column(db.String(64), nullable=True) # SHA-256 block hash tied to ledger
    product_photo = db.Column(db.String(255), nullable=True)
    payment_screenshot = db.Column(db.String(255), nullable=True)
    evidence_status = db.Column(db.String(30), default='Pending Review', nullable=False)
    evidence_reviewed_by = db.Column(db.String(120), nullable=True)

    def to_dict(self):
        latest_task = self.volunteer_tasks[-1] if (hasattr(self, 'volunteer_tasks') and self.volunteer_tasks) else None
        return {
            'id': self.id,
            'donor_id': self.donor_id,
            'donor_name': self.donor.name if self.donor else 'Anonymous',
            'donor_email': self.donor.email if self.donor else '',
            'donor_phone': self.donor.phone if self.donor else '',
            'donor_address': self.donor.address if self.donor else '',
            'type': self.type,
            'category': self.category,
            'item_name': self.item_name or '',
            'amount': round(self.amount or 0.0, 2),
            'quantity': self.quantity or 0.0,
            'unit': self.unit or ('INR' if self.type == 'Monetary' else 'units'),
            'status': self.status,
            'date': self.date.strftime('%Y-%m-%d %H:%M') if self.date else '',
            'notes': self.notes or '',
            'product_photo': self.product_photo or '',
            'payment_screenshot': self.payment_screenshot or '',
            'evidence_status': self.evidence_status or 'Pending Review',
            'evidence_reviewed_by': self.evidence_reviewed_by or '',
            'block_hash': self.block_hash or '',
            'verified': bool(self.block_hash),
            'volunteer_task': latest_task.to_dict(include_private=True) if latest_task else None
        }

