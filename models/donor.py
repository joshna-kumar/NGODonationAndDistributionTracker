from datetime import datetime
from database import db

class Donor(db.Model):
    __tablename__ = 'donors'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, index=True)
    phone = db.Column(db.String(50), nullable=True)
    address = db.Column(db.Text, nullable=True)
    preferred_causes = db.Column(db.String(255), nullable=True, default='General Fund')
    total_donated = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    donations = db.relationship('Donation', backref='donor', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone or '',
            'address': self.address or '',
            'preferred_causes': self.preferred_causes or 'General',
            'total_donated': round(self.total_donated or 0.0, 2),
            'donation_count': len(self.donations),
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else ''
        }
