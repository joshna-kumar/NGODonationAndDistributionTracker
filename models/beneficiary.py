from datetime import datetime
from database import db

class Beneficiary(db.Model):
    __tablename__ = 'beneficiaries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(120), nullable=False)
    contact = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    location = db.Column(db.String(150), nullable=False)
    eligibility_category = db.Column(db.String(80), nullable=False) # Emergency Relief, Low Income Family, Disabled Persons, Education Support, Medical Care
    status = db.Column(db.String(30), default='Active') # Active, Pending, Ineligible
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)

    # Relationships
    distributions = db.relationship('Distribution', backref='beneficiary', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'contact': self.contact or '',
            'email': self.email or '',
            'location': self.location,
            'eligibility_category': self.eligibility_category,
            'status': self.status,
            'registered_at': self.registered_at.strftime('%Y-%m-%d') if self.registered_at else '',
            'distributions_count': len(self.distributions),
            'notes': self.notes or ''
        }
