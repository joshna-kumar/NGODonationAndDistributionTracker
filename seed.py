from app import create_app
from database import db
from models import (
    User, Donor, Donation, InventoryItem, InventoryLog,
    Beneficiary, Distribution, DistributionItem, LedgerBlock, ActivityLog
)
from utils.blockchain import ensure_genesis_block, add_record_to_ledger, verify_ledger_integrity
from utils.helpers import log_activity


def seed_database():
    app = create_app()
    with app.app_context():
        print("Re-creating database tables...")
        db.drop_all()
        db.create_all()
        
        # 1. Initialize Genesis Block
        ensure_genesis_block()
        print("Genesis block initialized.")

        # 2. Create one Tamil Nadu demo user for each supported role
        users_data = [
            {'name': 'Joshna', 'email': 'admin@ngo.org', 'role': 'admin', 'phone': '+91 98765 43210'},
            {'name': 'Harish Kumar', 'email': 'staff@ngo.org', 'role': 'staff', 'phone': '+91 98765 43211'},
            {'name': 'Dia Ravi', 'email': 'donor@example.com', 'role': 'donor', 'phone': '+91 98765 43212'},
            {'name': 'Meena Devi', 'email': 'beneficiary@example.com', 'role': 'beneficiary', 'phone': '+91 98765 43213'},
            {'name': 'Kavya Raj', 'email': 'auditor@ngo.org', 'role': 'auditor', 'phone': '+91 98765 43214'},
        ]

        created_users = {}
        for udata in users_data:
            user = User(
                name=udata['name'],
                email=udata['email'],
                role=udata['role'],
                phone=udata['phone']
            )
            user.set_password('password123')
            db.session.add(user)
            db.session.flush()
            created_users[udata['role']] = user
            print(f"Created user: {user.email} [{user.role}]")

        db.session.commit()

        # 3. Create Donors
        donors_seed = [
            {'user_id': created_users['donor'].id, 'name': 'Dia Ravi', 'email': 'donor@example.com', 'phone': '+91 98765 43212', 'address': 'Anna Nagar, Chennai, Tamil Nadu', 'causes': 'Education Support'},
        ]

        created_donors = []
        for ddata in donors_seed:
            donor = Donor(
                user_id=ddata['user_id'],
                name=ddata['name'],
                email=ddata['email'],
                phone=ddata['phone'],
                address=ddata['address'],
                preferred_causes=ddata['causes'],
                total_donated=0.0
            )
            db.session.add(donor)
            db.session.flush()
            created_donors.append(donor)

        db.session.commit()
        print(f"Seeded {len(created_donors)} donor profiles.")

        # 4. Create Inventory Items
        inventory_seed = [
            {'category': 'Food', 'name': 'Tamil Nadu Rice Bags', 'quantity': 80.0, 'unit': 'bags', 'threshold': 5.0},
            {'category': 'Clothes', 'name': 'Family Clothing Sets', 'quantity': 80.0, 'unit': 'sets', 'threshold': 5.0},
            {'category': 'Blood', 'name': 'Blood Unit Supply', 'quantity': 80.0, 'unit': 'units', 'threshold': 5.0},
            {'category': 'Medical', 'name': 'First Aid Kits', 'quantity': 80.0, 'unit': 'kits', 'threshold': 5.0},
        ]

        created_inventory = {}
        for idata in inventory_seed:
            item = InventoryItem(
                category=idata['category'],
                name=idata['name'],
                quantity=idata['quantity'],
                unit=idata['unit'],
                low_stock_threshold=idata['threshold']
            )
            db.session.add(item)
            db.session.flush()
            created_inventory[idata['name']] = item

            # Log initial stock movement
            log = InventoryLog(
                inventory_item_id=item.id,
                movement_type='INBOUND',
                quantity=idata['quantity'],
                reference_type='MANUAL',
                notes='Initial warehouse stock check'
            )
            db.session.add(log)

        db.session.commit()
        print(f"Seeded {len(created_inventory)} inventory items.")

        # 5. Create Beneficiaries
        beneficiaries_seed = [
            {'user_id': created_users['beneficiary'].id, 'name': 'Meena Devi', 'email': 'beneficiary@example.com', 'contact': '+91 98765 43213', 'location': 'Madurai, Tamil Nadu', 'category': 'Low Income Family', 'status': 'Active'},
            {'user_id': None, 'name': 'Divya', 'email': 'divya.beneficiary@example.com', 'contact': '+91 98765 43222', 'location': 'Thiruvannamalai, Tamil Nadu', 'category': 'Low Income Family', 'status': 'Active'},
            {'user_id': None, 'name': 'Divya Dharshini', 'email': 'divyadharshini.beneficiary@example.com', 'contact': '+91 98765 43223', 'location': 'Kanchipuram, Tamil Nadu', 'category': 'Education Support', 'status': 'Active'},
            {'user_id': None, 'name': 'Nivetha', 'email': 'nivetha.beneficiary@example.com', 'contact': '+91 98765 43224', 'location': 'Erode, Tamil Nadu', 'category': 'Emergency Relief', 'status': 'Active'},
            {'user_id': None, 'name': 'Nivethitha', 'email': 'nivethitha.beneficiary@example.com', 'contact': '+91 98765 43225', 'location': 'Nagapattinam, Tamil Nadu', 'category': 'Medical Care', 'status': 'Active'},
            {'user_id': None, 'name': 'Anu', 'email': 'anu.beneficiary@example.com', 'contact': '+91 98765 43226', 'location': 'Dindigul, Tamil Nadu', 'category': 'Low Income Family', 'status': 'Active'},
            {'user_id': None, 'name': 'Barath', 'email': 'barath.beneficiary@example.com', 'contact': '+91 98765 43227', 'location': 'Tirunelveli, Tamil Nadu', 'category': 'Education Support', 'status': 'Active'},
            {'user_id': None, 'name': 'Kannan', 'email': 'kannan.beneficiary@example.com', 'contact': '+91 98765 43228', 'location': 'Sivagangai, Tamil Nadu', 'category': 'Disabled Persons', 'status': 'Active'},
        ]

        created_beneficiaries = []
        for bdata in beneficiaries_seed:
            ben = Beneficiary(
                user_id=bdata['user_id'],
                name=bdata['name'],
                email=bdata['email'],
                contact=bdata['contact'],
                location=bdata['location'],
                eligibility_category=bdata['category'],
                status=bdata['status']
            )
            db.session.add(ben)
            db.session.flush()
            created_beneficiaries.append(ben)

        db.session.commit()
        print(f"Seeded {len(created_beneficiaries)} beneficiaries.")

        # 6. Seed Donations and Write Ledger Blocks
        donations_seed = [
            {
                'donor': created_donors[0], # Dia
                'type': 'Monetary',
                'category': 'Money',
                'amount': 5000.0,
                'qty': 0,
                'unit': 'INR',
                'notes': 'Community support contribution for families in Tamil Nadu'
            },
            {
                'donor': created_donors[0],
                'type': 'In-Kind',
                'category': 'Food',
                'amount': 0.0,
                'qty': 100,
                'unit': 'kg',
                'notes': 'Rice and staple food donation for emergency relief'
            },
            {
                'donor': created_donors[0],
                'type': 'In-Kind',
                'category': 'Clothes',
                'amount': 0.0,
                'qty': 60,
                'unit': 'sets',
                'notes': 'Clean clothing sets for displaced families'
            },
            {
                'donor': created_donors[0],
                'type': 'In-Kind',
                'category': 'Blood',
                'amount': 0.0,
                'qty': 25,
                'unit': 'units',
                'notes': 'Blood units donated through the community drive'
            }
        ]

        for d in donations_seed:
            donor = d['donor']
            donation = Donation(
                donor_id=donor.id,
                type=d['type'],
                category=d['category'],
                amount=d['amount'],
                quantity=d['qty'],
                unit=d['unit'],
                status='Verified',
                notes=d['notes']
            )
            db.session.add(donation)
            db.session.flush()

            if d['type'] == 'Monetary':
                donor.total_donated = (donor.total_donated or 0.0) + d['amount']

            # Write Ledger Block
            payload = {
                'donation_id': donation.id,
                'donor_name': donor.name,
                'donor_email': donor.email,
                'type': d['type'],
                'category': d['category'],
                'value': f"₹{d['amount']:,.2f}" if d['type'] == 'Monetary' else f"{d['qty']} {d['unit']} ({d['category']})",
                'status': 'Verified',
                'notes': d['notes']
            }

            block = add_record_to_ledger('DONATION', donation.id, payload)
            donation.block_hash = block.block_hash
            print(f"Logged donation #{donation.id} -> Ledger Block #{block.index} ({block.block_hash[:16]}...)")

        db.session.commit()

        # 7. Seed Distributions and Write Ledger Blocks
        distributions_seed = [
            {
                'beneficiary': created_beneficiaries[0], # Meena
                'staff': created_users['staff'],
                'location': 'Madurai, Tamil Nadu',
                'notes': 'Food support distribution for a local family',
                'items': [
                    (created_inventory['Tamil Nadu Rice Bags'], 5.0)
                ]
            },
            {'beneficiary': created_beneficiaries[1], 'staff': created_users['staff'], 'location': 'Thiruvannamalai, Tamil Nadu', 'notes': 'Food and clothing aid delivered.', 'items': [(created_inventory['Tamil Nadu Rice Bags'], 5.0), (created_inventory['Family Clothing Sets'], 4.0)]},
            {'beneficiary': created_beneficiaries[2], 'staff': created_users['staff'], 'location': 'Kanchipuram, Tamil Nadu', 'notes': 'Education and medical support delivered.', 'items': [(created_inventory['First Aid Kits'], 3.0), (created_inventory['Family Clothing Sets'], 2.0)]},
            {'beneficiary': created_beneficiaries[3], 'staff': created_users['staff'], 'location': 'Erode, Tamil Nadu', 'notes': 'Emergency food and medical aid delivered.', 'items': [(created_inventory['Tamil Nadu Rice Bags'], 5.0), (created_inventory['First Aid Kits'], 3.0)]},
            {'beneficiary': created_beneficiaries[4], 'staff': created_users['staff'], 'location': 'Nagapattinam, Tamil Nadu', 'notes': 'Medical and blood support delivered.', 'items': [(created_inventory['Blood Unit Supply'], 2.0), (created_inventory['First Aid Kits'], 3.0)]},
            {'beneficiary': created_beneficiaries[5], 'staff': created_users['staff'], 'location': 'Dindigul, Tamil Nadu', 'notes': 'Food and clothing aid delivered.', 'items': [(created_inventory['Tamil Nadu Rice Bags'], 5.0), (created_inventory['Family Clothing Sets'], 3.0)]},
            {'beneficiary': created_beneficiaries[6], 'staff': created_users['staff'], 'location': 'Tirunelveli, Tamil Nadu', 'notes': 'Clothing and medical aid delivered.', 'items': [(created_inventory['Family Clothing Sets'], 3.0), (created_inventory['First Aid Kits'], 2.0)]},
            {'beneficiary': created_beneficiaries[7], 'staff': created_users['staff'], 'location': 'Sivagangai, Tamil Nadu', 'notes': 'Accessible medical and blood aid delivered.', 'items': [(created_inventory['Blood Unit Supply'], 2.0), (created_inventory['First Aid Kits'], 3.0)]}
        ]

        for dist_data in distributions_seed:
            ben = dist_data['beneficiary']
            staff = dist_data['staff']

            dist = Distribution(
                beneficiary_id=ben.id,
                donation_id=Donation.query.order_by(Donation.date.asc()).first().id,
                staff_id=staff.id,
                location=dist_data['location'],
                notes=dist_data['notes'],
                status='Completed'
            )
            db.session.add(dist)
            db.session.flush()

            summary_items = []
            for inv_item, qty in dist_data['items']:
                dist_item = DistributionItem(
                    distribution_id=dist.id,
                    inventory_item_id=inv_item.id,
                    quantity=qty
                )
                db.session.add(dist_item)

                # Deduct inventory stock
                inv_item.quantity -= qty

                inv_log = InventoryLog(
                    inventory_item_id=inv_item.id,
                    movement_type='OUTBOUND',
                    quantity=qty,
                    reference_type='DISTRIBUTION',
                    reference_id=dist.id,
                    notes=f'Dispatched to {ben.name}'
                )
                db.session.add(inv_log)
                summary_items.append(f"{qty} {inv_item.unit} of {inv_item.name}")

            # Write Ledger Block
            ledger_payload = {
                'distribution_id': dist.id,
                'beneficiary_name': ben.name,
                'beneficiary_location': dist_data['location'],
                'eligibility_category': ben.eligibility_category,
                'items': ", ".join(summary_items),
                'staff_member': staff.name
            }

            block = add_record_to_ledger('DISTRIBUTION', dist.id, ledger_payload)
            dist.block_hash = block.block_hash
            print(f"Logged distribution #{dist.id} -> Ledger Block #{block.index} ({block.block_hash[:16]}...)")

        db.session.commit()

        # 8. Seed Activity Log Entries
        activities = [
            ('SYSTEM_INIT', 'LEDGER', 0, 'Tamil Nadu NGO demo ledger initialized')
        ]
        for act in activities:
            log_activity(act[0], act[1], act[2], act[3])

        # 9. Verify Ledger Integrity
        verify_res = verify_ledger_integrity()
        print("\n=======================================================")
        print(f"SEEDING COMPLETE! Blockchain Ledger Status:")
        print(f"Valid: {verify_res['is_valid']}")
        print(f"Total Blocks: {verify_res['total_blocks']}")
        print(f"Message: {verify_res['message']}")
        print("=======================================================\n")

if __name__ == '__main__':
    seed_database()
