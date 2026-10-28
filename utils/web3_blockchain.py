import os
from datetime import datetime, timezone

from web3 import Web3


CONTRACT_ABI = [
    {
        'inputs': [
            {'internalType': 'uint256', 'name': 'distributionId', 'type': 'uint256'},
            {'internalType': 'uint256', 'name': 'donationId', 'type': 'uint256'},
            {'internalType': 'uint256', 'name': 'beneficiaryId', 'type': 'uint256'},
            {'internalType': 'uint256', 'name': 'amount', 'type': 'uint256'},
        ],
        'name': 'recordDistribution',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'uint256', 'name': 'distributionId', 'type': 'uint256'}],
        'name': 'getDistribution',
        'outputs': [
            {'internalType': 'uint256', 'name': 'distributionId', 'type': 'uint256'},
            {'internalType': 'uint256', 'name': 'donationId', 'type': 'uint256'},
            {'internalType': 'uint256', 'name': 'beneficiaryId', 'type': 'uint256'},
            {'internalType': 'uint256', 'name': 'amount', 'type': 'uint256'},
            {'internalType': 'uint256', 'name': 'timestamp', 'type': 'uint256'},
            {'internalType': 'address', 'name': 'sender', 'type': 'address'},
        ],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'name': 'recorded',
        'outputs': [{'internalType': 'bool', 'name': '', 'type': 'bool'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]


class BlockchainNotConfigured(Exception):
    pass


class BlockchainTransactionError(Exception):
    pass


def _settings():
    rpc_url = os.environ.get('BLOCKCHAIN_RPC_URL', '')
    private_key = os.environ.get('BLOCKCHAIN_PRIVATE_KEY', '')
    contract_address = os.environ.get('BLOCKCHAIN_CONTRACT_ADDRESS', '')
    if not rpc_url or not private_key or not contract_address:
        raise BlockchainNotConfigured(
            'Set BLOCKCHAIN_RPC_URL, BLOCKCHAIN_PRIVATE_KEY, and BLOCKCHAIN_CONTRACT_ADDRESS.'
        )
    return rpc_url, private_key, contract_address


def _client():
    rpc_url, private_key, contract_address = _settings()
    web3 = Web3(Web3.HTTPProvider(rpc_url))
    if not web3.is_connected():
        raise BlockchainTransactionError(f'Could not connect to blockchain RPC at {rpc_url}.')
    account = web3.eth.account.from_key(private_key)
    contract = web3.eth.contract(
        address=Web3.to_checksum_address(contract_address),
        abi=CONTRACT_ABI,
    )
    return web3, private_key, account.address, contract


def is_configured():
    try:
        _settings()
        return True
    except BlockchainNotConfigured:
        return False


def record_distribution(distribution_id, donation_id, beneficiary_id, amount):
    web3, private_key, sender, contract = _client()
    scaled_amount = int(round(float(amount) * 1000))
    try:
        nonce = web3.eth.get_transaction_count(sender)
        transaction = contract.functions.recordDistribution(
            int(distribution_id),
            int(donation_id),
            int(beneficiary_id),
            scaled_amount,
        ).build_transaction({
            'from': sender,
            'nonce': nonce,
            'chainId': web3.eth.chain_id,
            'gas': 300000,
            'gasPrice': web3.eth.gas_price,
        })
        signed = web3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            raise BlockchainTransactionError('Blockchain transaction was reverted.')
        return {
            'transaction_hash': web3.to_hex(tx_hash),
            'block_number': receipt.blockNumber,
            'sender': sender,
            'amount_scaled': scaled_amount,
        }
    except BlockchainTransactionError:
        raise
    except Exception as error:
        raise BlockchainTransactionError(str(error)) from error


def get_distribution(distribution_id):
    web3, _, _, contract = _client()
    try:
        record = contract.functions.getDistribution(int(distribution_id)).call()
        return {
            'distribution_id': record[0],
            'donation_id': record[1],
            'beneficiary_id': record[2],
            'amount': record[3] / 1000,
            'timestamp': record[4],
            'timestamp_iso': datetime.fromtimestamp(record[4], timezone.utc).isoformat(),
            'sender': record[5],
        }
    except Exception as error:
        raise BlockchainTransactionError(str(error)) from error
