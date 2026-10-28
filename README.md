# NGO Donation and Distribution Tracker

> A production-quality, transparent, and tamper-evident web application for managing NGO operations (Donors, Donations, Inventory, Beneficiaries, Distributions, Analytics, and a Custom Blockchain-based Integrity Ledger).

![Tech Stack](https://img.shields.io/badge/Python-Flask-blue)
![Database](https://img.shields.io/badge/SQLite-SQLAlchemy-green)
![Integrity](https://img.shields.io/badge/Blockchain-SHA--256-purple)
![Frontend](https://img.shields.io/badge/UI-Vanilla_JS_%2B_Pastel_Lavender-pink)

---

## 🌟 Key Features & Highlights

1. **SHA-256 Blockchain Transparency Ledger**
   - Every monetary donation, in-kind donation, and aid distribution event is immutably logged into a linked-list blockchain ledger.
   - Each block stores: `index`, `record_type`, `record_id`, `data_json`, `timestamp`, `previous_hash`, and `block_hash`.
   - **Live Tamper Detection:** Clicking **"Verify Ledger Integrity"** recomputes all SHA-256 hashes from scratch, verifying parent links and highlighting any tampered blocks with animated alerts.
   - **Simulate Tamper Demo:** Includes an interactive admin tool to test fraud detection live for evaluators.

2. **Role-Based Access Control (RBAC)**
   - **NGO Administrator:** Full control over users, donors, inventory, distributions, ledger verification, and system logs.
   - **NGO Staff:** Manage donations, inventory stock, beneficiary profiles, and log distributions.
   - **Donor:** Access personal donation history, impact summary ("Your donations helped X families"), and download official blockchain receipts.
   - **Beneficiary:** Access personal aid distribution history and eligibility category status.
   - **Auditor:** Read-only access to all records, analytics reports, activity logs, and ledger integrity verification tools.
   - **Volunteer:** Sees only assigned pickup/delivery tasks. Donor address and phone are provided only for an assigned pickup. Volunteers can opt in to GPS sharing per active task; pickup completion adds in-kind goods to inventory, and delivery completion records a beneficiary distribution. Volunteers cannot collect cash or access general donor/finance records.

3. **Soft Lavender Pastel Design System**
   - Styled with a soft, muted pastel lavender palette (`#C9B8E8`, `#E6DFF5`, `#5A4A82`, `#FBFAFE`).
   - Modern typography featuring **Poppins** (headings) and **Inter** (body text).
   - Soft rounded cards (12–20px radius), gentle drop shadows, smooth micro-animations (200–300ms ease), and responsive sidebar navigation.

4. **Real-Time Inventory Stock Tracking**
   - Tracks inbound stock (from in-kind donations) and outbound stock (from aid distributions).
   - Low-stock warning badges triggered automatically when stock drops below demand.

5. **Fuzzy Duplicate Donor Detection**
   - Detects potential duplicate donors based on email, phone number, or partial name matching.

6. **Interactive Analytics & Export**
   - Visual charts powered by **Chart.js** (donations by category, inventory levels vs. demand, beneficiaries by category).
   - One-click CSV export for donations, distributions, inventory, and ledger audit chain.

---

## 🏗️ Project Architecture

```
c:\Users\joshh\minime\
├── app.py                      # Flask app factory & entry point
├── config.py                   # App configuration & DB URI
├── database.py                 # SQLAlchemy db instance
├── seed.py                     # Database seeder with realistic test data
├── requirements.txt            # Dependencies (Flask, Flask-SQLAlchemy, Flask-Login, etc.)
├── models/                     # Database Models
│   ├── user.py                 # User & RBAC model
│   ├── donor.py                # Donor profile model
│   ├── donation.py             # Monetary & In-Kind donation model
│   ├── inventory.py            # InventoryItem & InventoryLog models
│   ├── beneficiary.py          # Beneficiary model
│   ├── distribution.py         # Distribution & DistributionItem models
│   ├── ledger.py               # LedgerBlock SHA-256 model
│   └── audit.py                # ActivityLog audit trail model
├── utils/
│   ├── blockchain.py           # Custom SHA-256 block creation & integrity check
│   ├── auth.py                 # RBAC permission decorators
│   └── helpers.py              # Activity logger, fuzzy matching & receipts
├── routes/                     # Flask API Blueprints
│   ├── auth.py                 # Auth & demo role switcher
│   ├── donors.py               # Donor CRUD & duplicate detection
│   ├── donations.py            # Donation recording & receipt API
│   ├── inventory.py            # Warehouse inventory & stock movement
│   ├── beneficiaries.py        # Beneficiary registration & history
│   ├── distributions.py        # Distribution dispatch & stock deduction
│   ├── ledger.py               # Blockchain viewing & verification
│   ├── reports.py              # Chart.js analytics & CSV export
│   └── audit.py                # System activity logs
├── static/                     # Frontend Assets
│   ├── css/style.css           # Soft Lavender pastel design system
│   └── js/                     # Frontend JS Controllers
│       ├── app.js              # SPA router, toast & modal manager
│       ├── auth.js             # Auth state & RBAC controller
│       ├── ledger.js           # Interactive Blockchain visualizer
│       ├── charts.js           # Chart.js analytics manager
│       └── modules.js          # Module renderers (Donors, Inventory, etc.)
└── templates/
    └── index.html              # Main SPA HTML shell
```

---

## ⚡ Quick Start Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Seed Database with Realistic Demo Data
```bash
python seed.py
```

### 3. Run Flask Application
```bash
python app.py
```
Or:
```bash
flask run
```

Access the application in your browser at: **`http://127.0.0.1:5000`**

### Cashfree payments

The monetary donation checkout uses Cashfree. For local sandbox testing, set `CASHFREE_APP_ID`, `CASHFREE_SECRET_KEY`, and `CASHFREE_ENVIRONMENT=sandbox` in the environment that starts Flask. Set `PUBLIC_BASE_URL` to the app's externally reachable HTTPS base URL so Cashfree can return to the app after checkout. Never expose the Cashfree secret key in browser code or commit real credentials.

### Public demo deployment on Render

The repository includes `render.yaml` as a starting point for a public demo deployment. Push the project to a Git provider, create a Render Blueprint from that repository, and set the Cashfree environment values in the Render service settings. After Render creates the public `onrender.com` URL, set `PUBLIC_BASE_URL` to that HTTPS URL and restart/redeploy the service. Keep Cashfree in sandbox mode until the account is approved for production payments.

The free demo service uses the app's SQLite database and local upload directory, which are not durable across all hosting restarts/redeploys. Use managed PostgreSQL and persistent/object storage before relying on it for real donor records or payment evidence.

---

## 🔑 Pre-Configured Test Accounts (Password for all: `password123`)

| Role | Email | Name | Capabilities |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@ngo.org` | Joshna | Full access, tamper testing, user management |
| **NGO Staff** | `staff@ngo.org` | Harish Kumar | Log donations, manage inventory & distributions |
| **Donor** | `donor@example.com` | Dia Ravi | View personal donations, impact summary, receipts |
| **Beneficiary** | `beneficiary@example.com` | Meena Devi | View received aid history & eligibility category |
| **Auditor** | `auditor@ngo.org` | Kavya Raj | Read-only access to all modules, reports, & ledger |

*Tip: Use the top **Evaluator Demo Bar** to toggle between personas instantly during review!*

---

## 🛡️ SHA-256 Blockchain Ledger Specification

## Volunteer task workflow

Donors and volunteers can self-register. Staff assign a volunteer either a donor goods pickup (donor address is required) or an inventory delivery to a beneficiary. The volunteer can start and stop GPS sharing for that task from a browser with location permission enabled; precise location is collected only while sharing is active. Pickup completion records an in-kind donation and inbound inventory movement. Delivery completion deducts inventory and records the distribution. Volunteers do not handle money through this workflow.

The roles in the application are Admin, NGO Staff, Donor, Beneficiary, Auditor, and Volunteer.

Each block hash is calculated as:
$$\text{Hash} = \text{SHA256}(\text{index} \parallel \text{record\_type} \parallel \text{record\_id} \parallel \text{data\_json} \parallel \text{previous\_hash} \parallel \text{timestamp})$$

1. **Genesis Block:** Automatically created at index 0.
2. **Sequential Linkage:** Block $N$ stores Block $N-1$'s hash in `previous_hash`.
3. **Integrity Check Algorithm:** Recomputes all hashes from genesis to tip, verifying parent pointer equality. Any discrepancy flags the exact block index as tampered.

---

## 📜 License
Developed for NGO Operations, Compliance & Auditability. Open source for non-profit and humanitarian use.
