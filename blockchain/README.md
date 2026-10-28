# Local blockchain setup

This project uses a local Ganache JSON-RPC network for the real ledger demonstration.

1. Install Node.js, then install Ganache:

```powershell
npm install --global ganache
```

2. Start Ganache in a separate terminal:

```powershell
ganache --chain.chainId 1337 --wallet.deterministic
```

3. Install Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

4. Compile and deploy the contract. The deploy command prints the contract address and deployer private key:

```powershell
python blockchain/deploy.py
```

5. Copy the printed values into `.env` using `.env.example` as a template, then start Flask:

```powershell
python app.py
```

For the current deterministic Ganache session, use:

```text
BLOCKCHAIN_RPC_URL=http://127.0.0.1:8545
BLOCKCHAIN_PRIVATE_KEY=0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d
BLOCKCHAIN_CONTRACT_ADDRESS=0xe78A0F7E598Cc8b0Bb87894B0F60dD2a88d6a8Ab
```

The private key above is for local Ganache only. Never use it on a public network.

The distribution workflow calls `recordDistribution` and stores the returned transaction hash in the database. If the blockchain variables are not configured, the existing local SHA-256 ledger remains available and the API reports that the real chain is not configured.
