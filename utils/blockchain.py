import hashlib
import json
from datetime import datetime
from database import db
from models.ledger import LedgerBlock

def calculate_block_hash(index, record_type, record_id, data_json_str, previous_hash, timestamp):
    """
    Computes SHA-256 hash for a block payload deterministically.
    """
    payload = f"{index}|{record_type}|{record_id or 0}|{data_json_str}|{previous_hash}|{timestamp}"
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()

def ensure_genesis_block():
    """
    Initializes genesis block if the ledger is empty.
    """
    existing_count = LedgerBlock.query.count()
    if existing_count == 0:
        ts = "2026-01-01 00:00:00"
        data_payload = {
            "title": "Genesis Block",
            "message": "NGO Immutable Ledger Initialized",
            "organization": "NGO Donation & Distribution Network",
            "compliance": "SHA-256 Audit Trail Active"
        }
        data_str = json.dumps(data_payload, sort_keys=True)
        prev_hash = "0" * 64
        genesis_hash = calculate_block_hash(0, "GENESIS", 0, data_str, prev_hash, ts)

        genesis_block = LedgerBlock(
            index=0,
            record_type="GENESIS",
            record_id=0,
            data_json=data_str,
            previous_hash=prev_hash,
            block_hash=genesis_hash,
            timestamp=ts
        )
        db.session.add(genesis_block)
        db.session.commit()
        return genesis_block

    return LedgerBlock.query.filter_by(index=0).first()

def add_record_to_ledger(record_type, record_id, data_payload):
    """
    Appends a new block to the blockchain ledger for a donation or distribution event.
    """
    ensure_genesis_block()

    last_block = LedgerBlock.query.order_by(LedgerBlock.index.desc()).first()
    new_index = last_block.index + 1
    prev_hash = last_block.block_hash
    ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    data_str = json.dumps(data_payload, sort_keys=True)
    block_hash = calculate_block_hash(new_index, record_type, record_id, data_str, prev_hash, ts)

    new_block = LedgerBlock(
        index=new_index,
        record_type=record_type,
        record_id=record_id,
        data_json=data_str,
        previous_hash=prev_hash,
        block_hash=block_hash,
        timestamp=ts
    )

    db.session.add(new_block)
    db.session.commit()
    return new_block

def verify_ledger_integrity():
    """
    Verifies the entire blockchain linked list by recomputing hashes from scratch
    and checking parent hash connections.
    """
    blocks = LedgerBlock.query.order_by(LedgerBlock.index.asc()).all()
    if not blocks:
        return {
            'is_valid': True,
            'total_blocks': 0,
            'tampered_blocks': [],
            'verified_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            'message': 'Ledger is empty'
        }

    tampered_blocks = []
    
    for i, block in enumerate(blocks):
        # 1. Recalculate expected block hash
        expected_hash = calculate_block_hash(
            block.index,
            block.record_type,
            block.record_id,
            block.data_json,
            block.previous_hash,
            block.timestamp
        )

        hash_valid = (block.block_hash == expected_hash)
        prev_hash_valid = True

        if i > 0:
            prev_block = blocks[i - 1]
            prev_hash_valid = (block.previous_hash == prev_block.block_hash)

        if not hash_valid or not prev_hash_valid:
            tampered_blocks.append({
                'id': block.id,
                'index': block.index,
                'record_type': block.record_type,
                'record_id': block.record_id,
                'stored_hash': block.block_hash,
                'recalculated_hash': expected_hash,
                'stored_prev_hash': block.previous_hash,
                'expected_prev_hash': blocks[i-1].block_hash if i > 0 else "0"*64,
                'hash_mismatch': not hash_valid,
                'chain_broken': not prev_hash_valid,
                'timestamp': block.timestamp
            })

    is_valid = len(tampered_blocks) == 0

    return {
        'is_valid': is_valid,
        'total_blocks': len(blocks),
        'tamper_count': len(tampered_blocks),
        'tampered_blocks': tampered_blocks,
        'verified_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        'message': 'All ledger blocks verified and tamper-free.' if is_valid else f'INTEGRITY FAILURE: {len(tampered_blocks)} tampered block(s) detected!'
    }

def simulate_tamper_block(block_index, tampered_note="Unauthorized DB Modification"):
    """
    Demo helper: Modifies block payload directly to demonstrate tamper detection in UI.
    """
    block = LedgerBlock.query.filter_by(index=block_index).first()
    if not block:
        return False, "Block not found"

    try:
        data = json.loads(block.data_json)
        data['TAMPERED_FLAG'] = True
        data['tamper_note'] = tampered_note
        data['tampered_amount'] = 999999
        block.data_json = json.dumps(data)
        db.session.commit()
        return True, f"Block #{block_index} successfully tampered for demo testing."
    except Exception as e:
        return False, str(e)

def repair_ledger_hashes():
    """
    Demo helper: Recomputes and restores valid hashes across all blocks.
    """
    blocks = LedgerBlock.query.order_by(LedgerBlock.index.asc()).all()
    if not blocks:
        return True, "No blocks"

    prev_hash = "0" * 64
    for i, block in enumerate(blocks):
        if i == 0:
            block.previous_hash = prev_hash
        else:
            block.previous_hash = blocks[i - 1].block_hash
        
        # Clean any tamper flag in JSON data if present
        try:
            data = json.loads(block.data_json)
            if 'TAMPERED_FLAG' in data:
                del data['TAMPERED_FLAG']
            if 'tamper_note' in data:
                del data['tamper_note']
            if 'tampered_amount' in data:
                del data['tampered_amount']
            block.data_json = json.dumps(data, sort_keys=True)
        except Exception:
            pass

        block.block_hash = calculate_block_hash(
            block.index,
            block.record_type,
            block.record_id,
            block.data_json,
            block.previous_hash,
            block.timestamp
        )

    db.session.commit()
    return True, "Ledger integrity repaired successfully."
