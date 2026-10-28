from datetime import datetime

from database import db


class AidRequest(db.Model):
    __tablename__ = 'aid_requests'

    id = db.Column(db.Integer, primary_key=True)
    beneficiary_id = db.Column(db.Integer, db.ForeignKey('beneficiaries.id'), nullable=False, index=True)
    category = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, nullable=False)
    urgency = db.Column(db.String(20), nullable=False, default='Normal')
    status = db.Column(db.String(30), nullable=False, default='Pending')
    staff_note = db.Column(db.Text, nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    beneficiary = db.relationship('Beneficiary', backref=db.backref('aid_requests', lazy=True, cascade='all, delete-orphan'))
    reviewed_by = db.relationship('User')

    def to_dict(self):
        return {
            'id': self.id,
            'beneficiary_id': self.beneficiary_id,
            'beneficiary_name': self.beneficiary.name if self.beneficiary else '',
            'category': self.category,
            'description': self.description,
            'urgency': self.urgency,
            'status': self.status,
            'staff_note': self.staff_note or '',
            'reviewed_by': self.reviewed_by.name if self.reviewed_by else '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else '',
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else ''
        }
