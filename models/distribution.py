from datetime import datetime
from database import db

class Distribution(db.Model):
    __tablename__ = 'distributions'

    id = db.Column(db.Integer, primary_key=True)
    beneficiary_id = db.Column(db.Integer, db.ForeignKey('beneficiaries.id'), nullable=False)
    donation_id = db.Column(db.Integer, db.ForeignKey('donations.id'), nullable=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    location = db.Column(db.String(150), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    amount = db.Column(db.Float, default=0.0) # Monetary aid amount
    status = db.Column(db.String(30), default='Completed')
    block_hash = db.Column(db.String(64), nullable=True) # Blockchain ledger block hash
    blockchain_transaction_hash = db.Column(db.String(66), nullable=True)

    # Relationships
    items = db.relationship('DistributionItem', backref='distribution', lazy=True, cascade='all, delete-orphan')
    staff = db.relationship('User', foreign_keys=[staff_id])

    def to_dict(self):
        return {
            'id': self.id,
            'beneficiary_id': self.beneficiary_id,
            'donation_id': self.donation_id,
            'beneficiary_name': self.beneficiary.name if self.beneficiary else 'Unknown',
            'beneficiary_category': self.beneficiary.eligibility_category if self.beneficiary else '',
            'staff_id': self.staff_id,
            'staff_name': self.staff.name if self.staff else 'NGO Staff',
            'date': self.date.strftime('%Y-%m-%d %H:%M') if self.date else '',
            'location': self.location,
            'notes': self.notes or '',
            'amount': round(self.amount or 0.0, 2),
            'donor_name': self.donation.donor.name if (self.donation and self.donation.donor) else '',
            'donor_email': self.donation.donor.email if (self.donation and self.donation.donor) else '',
            'status': self.status,
            'block_hash': self.block_hash or '',
            'blockchain_transaction_hash': self.blockchain_transaction_hash or '',
            'items': [item.to_dict() for item in self.items]
        }

class DistributionItem(db.Model):
    __tablename__ = 'distribution_items'

    id = db.Column(db.Integer, primary_key=True)
    distribution_id = db.Column(db.Integer, db.ForeignKey('distributions.id'), nullable=False)
    inventory_item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)

    # Relationships
    inventory_item = db.relationship('InventoryItem')

    def to_dict(self):
        return {
            'id': self.id,
            'distribution_id': self.distribution_id,
            'inventory_item_id': self.inventory_item_id,
            'item_name': self.inventory_item.name if self.inventory_item else 'Unknown Item',
            'category': self.inventory_item.category if self.inventory_item else '',
            'quantity': self.quantity,
            'unit': self.inventory_item.unit if self.inventory_item else 'units'
        }
