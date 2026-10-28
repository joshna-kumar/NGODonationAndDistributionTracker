from datetime import datetime
import json
from database import db

class LedgerBlock(db.Model):
    __tablename__ = 'ledger_blocks'

    id = db.Column(db.Integer, primary_key=True)
    index = db.Column(db.Integer, nullable=False, unique=True, index=True)
    record_type = db.Column(db.String(30), nullable=False) # 'DONATION', 'DISTRIBUTION', 'GENESIS'
    record_id = db.Column(db.Integer, nullable=True)
    data_json = db.Column(db.Text, nullable=False) # JSON payload string
    previous_hash = db.Column(db.String(64), nullable=False)
    block_hash = db.Column(db.String(64), nullable=False, unique=True)
    timestamp = db.Column(db.String(30), nullable=False)

    def to_dict(self):
        try:
            parsed_data = json.loads(self.data_json)
        except Exception:
            parsed_data = self.data_json

        return {
            'id': self.id,
            'index': self.index,
            'record_type': self.record_type,
            'record_id': self.record_id,
            'data': parsed_data,
            'previous_hash': self.previous_hash,
            'block_hash': self.block_hash,
            'timestamp': self.timestamp
        }
