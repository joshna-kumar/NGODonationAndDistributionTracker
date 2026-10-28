from datetime import datetime

from database import db


class CashfreeOrder(db.Model):
    __tablename__ = 'cashfree_orders'

    order_id = db.Column(db.String(80), primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey('donors.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='ACTIVE')
    donation_id = db.Column(db.Integer, db.ForeignKey('donations.id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    donor = db.relationship('Donor')
    donation = db.relationship('Donation')