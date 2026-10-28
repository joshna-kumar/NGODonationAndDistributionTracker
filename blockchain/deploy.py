import json
import os
from pathlib import Path

from solcx import compile_source, install_solc
from web3 import Web3


ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT / 'blockchain' / 'contracts' / 'DonationLedger.sol'
SOLC_VERSION = '0.8.20'


def main():
    rpc_url = os.environ.get('BLOCKCHAIN_RPC_URL', 'http://127.0.0.1:8545')
    private_key = os.environ.get('BLOCKCHAIN_PRIVATE_KEY', '')
    web3 = Web3(Web3.HTTPProvider(rpc_url))
    if not web3.is_connected():
        raise SystemExit(f'Cannot connect to {rpc_url}. Start Ganache first.')

    install_solc(SOLC_VERSION)
    source = CONTRACT_PATH.read_text(encoding='utf-8')
    compiled = compile_source(source, solc_version=SOLC_VERSION)
    _, contract_data = compiled.popitem()
    abi = contract_data['abi']
    bytecode = contract_data['bin']
    contract = web3.eth.contract(abi=abi, bytecode=bytecode)

    if private_key:
        account = web3.eth.account.from_key(private_key)
        transaction = contract.constructor().build_transaction({
            'from': account.address,
            'nonce': web3.eth.get_transaction_count(account.address),
            'chainId': web3.eth.chain_id,
            'gas': 3000000,
            'gasPrice': web3.eth.gas_price,
        })
        signed = web3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    else:
        accounts = web3.eth.accounts
        if not accounts:
            raise SystemExit('No unlocked Ganache account was found.')
        account = accounts[0]
        tx_hash = contract.constructor().transact({'from': account})

    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    address = receipt.contractAddress
    print(json.dumps({
        'contract_address': address,
        'deployment_transaction': web3.to_hex(tx_hash),
        'rpc_url': rpc_url,
        'deployer_address': account.address if hasattr(account, 'address') else account,
    }, indent=2))
    print(f'BLOCKCHAIN_CONTRACT_ADDRESS={address}')


if __name__ == '__main__':
    main()
