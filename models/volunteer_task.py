from datetime import datetime

from database import db


class VolunteerTask(db.Model):
    __tablename__ = 'volunteer_tasks'

    id = db.Column(db.Integer, primary_key=True)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    task_type = db.Column(db.String(20), nullable=False)
    donor_id = db.Column(db.Integer, db.ForeignKey('donors.id'), nullable=True)
    donation_id = db.Column(db.Integer, db.ForeignKey('donations.id'), nullable=True)
    beneficiary_id = db.Column(db.Integer, db.ForeignKey('beneficiaries.id'), nullable=True)
    inventory_item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=True)
    item_name = db.Column(db.String(120), nullable=True)
    category = db.Column(db.String(80), nullable=True)
    unit = db.Column(db.String(30), nullable=True)
    expected_quantity = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(30), nullable=False, default='Assigned')
    notes = db.Column(db.Text, nullable=True)
    location_sharing = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    volunteer = db.relationship('User')
    donor = db.relationship('Donor')
    donation = db.relationship('Donation', backref=db.backref('volunteer_tasks', lazy=True, order_by='VolunteerTask.id'))
    beneficiary = db.relationship('Beneficiary')
    inventory_item = db.relationship('InventoryItem')
    locations = db.relationship(
        'VolunteerLocation',
        backref='task',
        lazy=True,
        cascade='all, delete-orphan',
        order_by='VolunteerLocation.captured_at'
    )

    def to_dict(self, include_private=False):
        latest_location = self.locations[-1] if self.locations else None
        data = {
            'id': self.id,
            'task_type': self.task_type,
            'status': self.status,
            'donation_id': self.donation_id,
            'item_name': self.item_name or (self.inventory_item.name if self.inventory_item else ''),
            'category': self.category or (self.inventory_item.category if self.inventory_item else ''),
            'unit': self.unit or (self.inventory_item.unit if self.inventory_item else ''),
            'expected_quantity': self.expected_quantity or 0,
            'beneficiary_name': self.beneficiary.name if self.beneficiary else '',
            'beneficiary_location': self.beneficiary.location if self.beneficiary else '',
            'notes': self.notes or '',
            'location_sharing': self.location_sharing,
            'latest_location': latest_location.to_dict() if latest_location and include_private else None,
            'location_history': [location.to_dict() for location in self.locations] if include_private else [],
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else '',
            'completed_at': self.completed_at.strftime('%Y-%m-%d %H:%M') if self.completed_at else ''
        }
        if include_private:
            data.update({
                'volunteer_id': self.volunteer_id,
                'volunteer_name': self.volunteer.name if self.volunteer else 'Unassigned',
                'volunteer_phone': self.volunteer.phone if self.volunteer else '',
                'volunteer_email': self.volunteer.email if self.volunteer else '',
                'donor_id': self.donor_id,
                'donor_name': self.donor.name if self.donor else '',
                'donor_address': self.donor.address if self.donor else '',
                'donor_phone': self.donor.phone if self.donor else '',
                'donor_email': self.donor.email if self.donor else '',
                'donor_preferred_causes': self.donor.preferred_causes if self.donor else '',
                'beneficiary_id': self.beneficiary_id,
                'inventory_item_id': self.inventory_item_id
            })
        return data


class VolunteerLocation(db.Model):
    __tablename__ = 'volunteer_locations'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('volunteer_tasks.id'), nullable=False, index=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    accuracy_meters = db.Column(db.Float, nullable=True)
    captured_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'accuracy_meters': self.accuracy_meters,
            'captured_at': self.captured_at.strftime('%Y-%m-%d %H:%M:%S')
        }
