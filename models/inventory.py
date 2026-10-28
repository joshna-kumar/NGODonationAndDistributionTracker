from datetime import datetime
from database import db

class InventoryItem(db.Model):
    __tablename__ = 'inventory_items'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(80), nullable=False) # Food, Medical, Clothing, Education, Shelter, Hygiene
    name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Float, default=0.0)
    unit = db.Column(db.String(30), default='units') # kg, boxes, kits, packs, liters
    low_stock_threshold = db.Column(db.Float, default=10.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    logs = db.relationship('InventoryLog', backref='item', lazy=True, cascade='all, delete-orphan')

    @property
    def is_low_stock(self):
        return self.quantity <= self.low_stock_threshold

    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'name': self.name,
            'quantity': round(self.quantity or 0.0, 2),
            'unit': self.unit,
            'low_stock_threshold': round(self.low_stock_threshold or 0.0, 2),
            'is_low_stock': self.is_low_stock,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else ''
        }

class InventoryLog(db.Model):
    __tablename__ = 'inventory_logs'

    id = db.Column(db.Integer, primary_key=True)
    inventory_item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=False)
    movement_type = db.Column(db.String(20), nullable=False) # 'INBOUND', 'OUTBOUND', 'ADJUSTMENT'
    quantity = db.Column(db.Float, nullable=False)
    reference_type = db.Column(db.String(30), nullable=True) # 'DONATION', 'DISTRIBUTION', 'MANUAL'
    reference_id = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'inventory_item_id': self.inventory_item_id,
            'item_name': self.item.name if self.item else 'Unknown',
            'movement_type': self.movement_type,
            'quantity': self.quantity,
            'reference_type': self.reference_type or 'MANUAL',
            'reference_id': self.reference_id,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else '',
            'notes': self.notes or ''
        }
