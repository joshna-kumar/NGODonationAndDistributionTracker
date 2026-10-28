import requests
import json
import sys

BASE_URL = "http://127.0.0.1:5000"

def test_full_live_goods_flow():
    print("=== STARTING LIVE END-TO-END GOODS DONATION WORKFLOW ===")
    
    # 1. DONOR LOGIN & GOODS DONATION
    donor_session = requests.Session()
    res = donor_session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "donor@example.com",
        "password": "password123",
        "role": "donor"
    })
    assert res.status_code == 200, f"Donor login failed: {res.text}"
    donor_user = res.json()["user"]
    print(f"[OK] 1. Logged in as Donor: {donor_user['name']} ({donor_user['email']})")

    donation_payload = {
        "type": "In-Kind",
        "category": "Goods",
        "item_name": "Emergency Solar Lanterns",
        "quantity": "20",
        "unit": "boxes",
        "donor_phone": "+91 98765 43212",
        "donor_address": "42 Anna Salai, Chennai, Tamil Nadu",
        "notes": "Fragile items packed with care. Call before arriving."
    }
    res = donor_session.post(f"{BASE_URL}/api/donations", data=donation_payload)
    assert res.status_code == 201, f"Create donation failed: {res.text}"
    donation_data = res.json()["donation"]
    donation_id = donation_data["id"]
    print(f"[OK] 2. Donor created goods donation #{donation_id}: {donation_data['item_name']} ({donation_data['quantity']} {donation_data['unit']}), Status: {donation_data['status']}")

    # 2. STAFF LOGIN & VIEW PENDING GOODS DONATIONS
    staff_session = requests.Session()
    res = staff_session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "staff@ngo.org",
        "password": "password123",
        "role": "staff"
    })
    assert res.status_code == 200, f"Staff login failed: {res.text}"
    staff_user = res.json()["user"]
    print(f"[OK] 3. Logged in as Staff: {staff_user['name']}")

    res = staff_session.get(f"{BASE_URL}/api/volunteer-tasks/pending-donations")
    assert res.status_code == 200, f"Staff pending list failed: {res.text}"
    pending_list = res.json()["pending_goods_donations"]
    target = next((d for d in pending_list if d["id"] == donation_id), None)
    assert target is not None, f"Donation {donation_id} not found in staff pending goods list!"
    print(f"[OK] 4. Staff sees pending goods donation:")
    print(f"      - Donor Name: {target['donor_name']}")
    print(f"      - Donor Phone: {target['donor_phone']}")
    print(f"      - Pickup Address: {target['donor_address']}")
    print(f"      - Goods: {target['item_name']} ({target['quantity']} {target['unit']})")
    assert target["donor_phone"] == "+91 98765 43212"
    assert target["donor_address"] == "42 Anna Salai, Chennai, Tamil Nadu"

    # Get volunteer list
    res = staff_session.get(f"{BASE_URL}/api/volunteer-tasks/volunteers")
    assert res.status_code == 200
    volunteers = res.json()["volunteers"]
    arun = next((v for v in volunteers if v["email"] == "volunteer@ngo.org"), volunteers[0])
    print(f"[OK] 5. Staff assigns task to volunteer: {arun['name']} (ID: {arun['id']})")

    # Staff assigns task
    res = staff_session.post(f"{BASE_URL}/api/volunteer-tasks", json={
        "task_type": "pickup",
        "donation_id": donation_id,
        "volunteer_id": arun["id"]
    })
    assert res.status_code == 201, f"Task assignment failed: {res.text}"
    task_id = res.json()["task"]["id"]
    print(f"[OK] 6. Task #{task_id} assigned to volunteer {arun['name']}")

    # 3. VOLUNTEER LOGIN & TASK VIEW
    volunteer_session = requests.Session()
    res = volunteer_session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "volunteer@ngo.org",
        "password": "password123",
        "role": "volunteer"
    })
    assert res.status_code == 200, f"Volunteer login failed: {res.text}"
    volunteer_user = res.json()["user"]
    print(f"[OK] 7. Logged in as Volunteer: {volunteer_user['name']}")

    res = volunteer_session.get(f"{BASE_URL}/api/volunteer-tasks")
    assert res.status_code == 200
    tasks = res.json()["tasks"]
    # Verify ONLY assigned tasks for this volunteer are returned
    for t in tasks:
        assert t["volunteer_id"] == volunteer_user["id"], "Volunteer saw someone else's task!"
    my_task = next((t for t in tasks if t["id"] == task_id), None)
    assert my_task is not None, f"Assigned task {task_id} not visible to volunteer!"
    print(f"[OK] 8. Volunteer sees assigned task #{task_id} with donor details:")
    print(f"      - Donor Name: {my_task['donor_name']}")
    print(f"      - Donor Phone: {my_task['donor_phone']}")
    print(f"      - Pickup Address: {my_task['donor_address']}")
    print(f"      - Item: {my_task['item_name']} ({my_task['expected_quantity']} {my_task['unit']})")

    # 4. VOLUNTEER ACCEPTS TASK
    res = volunteer_session.post(f"{BASE_URL}/api/volunteer-tasks/{task_id}/status", json={
        "status": "Accepted"
    })
    assert res.status_code == 200, f"Accept task failed: {res.text}"
    print(f"[OK] 9. Volunteer accepted task #{task_id}")

    # 5. VOLUNTEER SHARES LOCATION
    res = volunteer_session.post(f"{BASE_URL}/api/volunteer-tasks/{task_id}/location", json={
        "action": "start",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "accuracy_meters": 12.0
    })
    assert res.status_code == 200, f"Share location failed: {res.text}"
    print(f"[OK] 10. Volunteer shared GPS location: Lat 13.0827, Lng 80.2707")

    # Verify donor can read the location
    res = donor_session.get(f"{BASE_URL}/api/volunteer-tasks/{task_id}/location")
    assert res.status_code == 200, f"Donor could not fetch location: {res.text}"
    loc_data = res.json()
    assert loc_data["location_sharing"] is True
    assert loc_data["latest_location"]["latitude"] == 13.0827
    print(f"[OK] 11. Donor successfully received live volunteer location in real-time!")

    # 6. VOLUNTEER ADVANCES TO "At Donor's Location"
    res = volunteer_session.post(f"{BASE_URL}/api/volunteer-tasks/{task_id}/status", json={
        "status": "At Donor's Location"
    })
    assert res.status_code == 200, f"Status update to 'At Donor's Location' failed: {res.text}"
    print(f"[OK] 12. Volunteer status updated to: At Donor's Location")

    # 7. VOLUNTEER ADVANCES TO "Picked Up"
    res = volunteer_session.post(f"{BASE_URL}/api/volunteer-tasks/{task_id}/status", json={
        "status": "Picked Up"
    })
    assert res.status_code == 200, f"Status update to 'Picked Up' failed: {res.text}"
    print(f"[OK] 13. Volunteer status updated to: Picked Up")

    # 8. VOLUNTEER SENDS TO INVENTORY
    res = volunteer_session.post(f"{BASE_URL}/api/volunteer-tasks/{task_id}/status", json={
        "status": "Sent to Inventory",
        "quantity": 20
    })
    assert res.status_code == 200, f"Status update to 'Sent to Inventory' failed: {res.text}"
    print(f"[OK] 14. Volunteer completed task with: Sent to Inventory (Quantity: 20)")

    # 9. DONOR TRACKS COMPLETION
    res = donor_session.get(f"{BASE_URL}/api/donations")
    assert res.status_code == 200
    my_donations = res.json()["donations"]
    my_d = next((d for d in my_donations if d["id"] == donation_id), None)
    assert my_d is not None
    print(f"[OK] 15. Donor refreshed donations list:")
    print(f"      - Final Donation Status: {my_d['status']}")
    print(f"      - Volunteer Task Status: {my_d['volunteer_task']['status']}")
    print(f"      - Verified in Ledger & Inventory: {my_d['verified']}")
    assert my_d["status"] == "Received in Inventory"
    assert my_d["volunteer_task"]["status"] == "Sent to Inventory"

    print("\n>>> ALL WORKFLOW STEPS VERIFIED 100% WORKING SUCCESSFULLY! <<<")

if __name__ == "__main__":
    try:
        test_full_live_goods_flow()
    except Exception as e:
        print(f"\n[FAILED]: {e}")
        sys.exit(1)
