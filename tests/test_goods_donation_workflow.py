import uuid
import unittest

from app import create_app
from database import db
from models.donation import Donation
from models.donor import Donor
from models.inventory import InventoryItem
from models.user import User
from models.volunteer_task import VolunteerTask


class GoodsDonationWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_complete_goods_donation_volunteer_tracking_flow(self):
        uid = uuid.uuid4().hex[:8]
        donor_email = f"donor-{uid}@example.test"
        staff_email = f"staff-{uid}@example.test"
        vol_email = f"vol-{uid}@example.test"
        other_vol_email = f"other-vol-{uid}@example.test"

        # 1. Register Donor with Phone
        donor_res = self.client.post('/api/auth/register', json={
            'name': f'Donor {uid}',
            'email': donor_email,
            'password': 'password123',
            'phone': '9876543210',
            'role': 'donor'
        })
        self.assertEqual(donor_res.status_code, 201)

        # Create staff, volunteer, and other_volunteer accounts
        with self.app.app_context():
            staff = User(name=f'Staff {uid}', email=staff_email, role='staff', phone='9876543211')
            staff.set_password('password123')
            vol = User(name=f'Volunteer {uid}', email=vol_email, role='volunteer', phone='9876543215')
            vol.set_password('password123')
            other_vol = User(name=f'Other Vol {uid}', email=other_vol_email, role='volunteer', phone='9876543216')
            other_vol.set_password('password123')
            db.session.add_all([staff, vol, other_vol])
            db.session.commit()
            vol_id = vol.id
            other_vol_id = other_vol.id

        # 2. Donor makes a Goods donation (category != 'Money')
        item_title = f'Emergency Warm Blankets {uid}'
        donation_res = self.client.post('/api/donations', data={
            'category': 'Goods',
            'type': 'In-Kind',
            'item_name': item_title,
            'quantity': '25',
            'unit': 'blankets',
            'notes': 'Please call before arriving',
            'donor_phone': '9876543210',
            'donor_address': 'Flat 402, Lotus Towers, T Nagar, Chennai'
        })
        self.assertEqual(donation_res.status_code, 201)
        donation_data = donation_res.get_json()['donation']
        donation_id = donation_data['id']
        self.assertEqual(donation_data['donor_phone'], '9876543210')
        self.assertEqual(donation_data['donor_address'], 'Flat 402, Lotus Towers, T Nagar, Chennai')
        self.assertEqual(donation_data['status'], 'Pending Pickup')

        # 3. Staff logs in and views the Goods donation
        staff_client = self.app.test_client()
        staff_login = staff_client.post('/api/auth/login', json={
            'email': staff_email,
            'password': 'password123',
            'role': 'staff'
        })
        self.assertEqual(staff_login.status_code, 200)

        # Check pending goods donations endpoint for staff
        pending_res = staff_client.get('/api/volunteer-tasks/pending-donations')
        self.assertEqual(pending_res.status_code, 200)
        pending_list = pending_res.get_json()['pending_donations']
        matched_pending = next((d for d in pending_list if d['id'] == donation_id), None)
        self.assertIsNotNone(matched_pending)
        self.assertEqual(matched_pending['donor_name'], f'Donor {uid}')
        self.assertEqual(matched_pending['donor_phone'], '9876543210')
        self.assertEqual(matched_pending['donor_address'], 'Flat 402, Lotus Towers, T Nagar, Chennai')
        self.assertEqual(matched_pending['quantity'], 25)
        self.assertEqual(matched_pending['unit'], 'blankets')

        # Staff assigns this task to volunteer
        assign_res = staff_client.post('/api/volunteer-tasks', json={
            'task_type': 'pickup',
            'donation_id': donation_id,
            'volunteer_id': vol_id,
            'notes': 'Collect from security gate'
        })
        self.assertEqual(assign_res.status_code, 201)
        task_id = assign_res.get_json()['task']['id']

        # 4. Volunteer logs in
        vol_client = self.app.test_client()
        vol_login = vol_client.post('/api/auth/login', json={
            'email': vol_email,
            'password': 'password123',
            'role': 'volunteer'
        })
        self.assertEqual(vol_login.status_code, 200)

        # Volunteer page: only assigned task is visible with donor information
        vol_tasks_res = vol_client.get('/api/volunteer-tasks')
        self.assertEqual(vol_tasks_res.status_code, 200)
        vol_tasks = vol_tasks_res.get_json()['tasks']
        self.assertEqual(len(vol_tasks), 1)
        my_task = vol_tasks[0]
        self.assertEqual(my_task['id'], task_id)
        self.assertEqual(my_task['donor_name'], f'Donor {uid}')
        self.assertEqual(my_task['donor_phone'], '9876543210')
        self.assertEqual(my_task['donor_address'], 'Flat 402, Lotus Towers, T Nagar, Chennai')
        self.assertEqual(my_task['item_name'], item_title)
        self.assertEqual(my_task['expected_quantity'], 25)

        # Other volunteer sees nothing
        other_vol_client = self.app.test_client()
        other_vol_client.post('/api/auth/login', json={
            'email': other_vol_email,
            'password': 'password123',
            'role': 'volunteer'
        })
        self.assertEqual(other_vol_client.get('/api/volunteer-tasks').get_json()['tasks'], [])

        # 5. Volunteer accepts the task
        accept_res = vol_client.post(f'/api/volunteer-tasks/{task_id}/status', json={'status': 'Accepted'})
        self.assertEqual(accept_res.status_code, 200)

        # 6. Volunteer shares location
        loc_res = vol_client.post(f'/api/volunteer-tasks/{task_id}/location', json={
            'action': 'start',
            'latitude': 13.0418,
            'longitude': 80.2341,
            'accuracy_meters': 5.0
        })
        self.assertEqual(loc_res.status_code, 200)
        self.assertTrue(loc_res.get_json()['task']['location_sharing'])

        # Staff can view the volunteer's shared location
        staff_loc_res = staff_client.get(f'/api/volunteer-tasks/{task_id}/location')
        self.assertEqual(staff_loc_res.status_code, 200)
        self.assertEqual(staff_loc_res.get_json()['latest_location']['latitude'], 13.0418)

        # Donor can also view the volunteer's shared location
        donor_loc_res = self.client.get(f'/api/volunteer-tasks/{task_id}/location')
        self.assertEqual(donor_loc_res.status_code, 200)
        self.assertEqual(donor_loc_res.get_json()['latest_location']['latitude'], 13.0418)

        # 7. Volunteer updates status: 'At Donor\'s Location'
        at_loc_res = vol_client.post(f'/api/volunteer-tasks/{task_id}/status', json={'status': "At Donor's Location"})
        self.assertEqual(at_loc_res.status_code, 200)
        self.assertEqual(at_loc_res.get_json()['task']['status'], "At Donor's Location")

        # Reflected to the donor
        donor_task_check = self.client.get('/api/volunteer-tasks').get_json()['tasks'][0]
        self.assertEqual(donor_task_check['status'], "At Donor's Location")

        # 8. Volunteer updates status: 'Picked Up'
        picked_res = vol_client.post(f'/api/volunteer-tasks/{task_id}/status', json={'status': 'Picked Up'})
        self.assertEqual(picked_res.status_code, 200)

        # Reflected to the donor
        donor_task_check = self.client.get('/api/volunteer-tasks').get_json()['tasks'][0]
        self.assertEqual(donor_task_check['status'], 'Picked Up')

        # 9. Volunteer updates status: 'Sent to Inventory' (completed with collected quantity)
        complete_res = vol_client.post(f'/api/volunteer-tasks/{task_id}/status', json={
            'status': 'Sent to Inventory',
            'quantity': 25
        })
        self.assertEqual(complete_res.status_code, 200)
        self.assertEqual(complete_res.get_json()['task']['status'], 'Sent to Inventory')

        # Check stock and donation record updated
        with self.app.app_context():
            stock = InventoryItem.query.filter_by(name=item_title).first()
            self.assertIsNotNone(stock)
            self.assertEqual(stock.quantity, 25)
            don = db.session.get(Donation, donation_id)
            self.assertEqual(don.status, 'Received in Inventory')
            self.assertIsNotNone(don.block_hash)

        # Reflected to the donor on tracking
        donor_donations = self.client.get('/api/donations').get_json()['donations']
        matched_donation = next(d for d in donor_donations if d['id'] == donation_id)
        self.assertEqual(matched_donation['status'], 'Received in Inventory')
        self.assertIsNotNone(matched_donation['volunteer_task'])
        self.assertEqual(matched_donation['volunteer_task']['status'], 'Sent to Inventory')


if __name__ == '__main__':
    unittest.main()
