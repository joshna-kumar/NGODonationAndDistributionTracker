from datetime import datetime
from database import db

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user_name = db.Column(db.String(120), nullable=True, default='System')
    user_role = db.Column(db.String(30), nullable=True, default='System')
    action = db.Column(db.String(50), nullable=False) # 'CREATE', 'UPDATE', 'DELETE', 'VERIFY', 'LOGIN', 'TAMPER'
    entity = db.Column(db.String(50), nullable=False) # 'DONATION', 'DISTRIBUTION', 'INVENTORY', 'BENEFICIARY', 'DONOR', 'LEDGER', 'USER'
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user_name or 'system',
            'user_role': self.user_role or 'System',
            'action': self.action,
            'entity': self.entity,
            'entity_id': self.entity_id,
            'details': self.details or '',
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else ''
        }
