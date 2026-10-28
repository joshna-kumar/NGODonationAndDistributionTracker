import uuid
import unittest

from app import create_app
from database import db
from models.beneficiary import Beneficiary
from models.distribution import Distribution
from models.donation import Donation
from models.donor import Donor
from models.inventory import InventoryItem
from models.user import User
from models.volunteer_task import VolunteerTask


class VolunteerWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_volunteer_can_register_without_creating_donor_profile(self):
        email = f'volunteer-{uuid.uuid4().hex}@example.test'
        response = self.client.post('/api/auth/register', json={
            'name': 'Test Volunteer',
            'email': email,
            'password': 'test-password',
            'phone': '5551234567',
            'role': 'volunteer'
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()['user']['role'], 'volunteer')
        self.assertEqual(self.client.get('/api/volunteer-tasks').get_json()['tasks'], [])
        self.assertEqual(self.client.get('/api/donors').status_code, 403)

    def test_volunteer_can_only_read_own_task_and_donor_address(self):
        unique_id = uuid.uuid4().hex
        with self.app.app_context():
            volunteer = User(name='Assigned Volunteer', email=f'assigned-{unique_id}@example.test', role='volunteer')
            other_volunteer = User(name='Other Volunteer', email=f'other-{unique_id}@example.test', role='volunteer')
            staff = User(name='Task Staff', email=f'staff-{unique_id}@example.test', role='staff')
            donor = Donor(name='Pickup Donor', email=f'donor-{unique_id}@example.test', address='Private pickup address')
            for user in (volunteer, other_volunteer, staff):
                user.set_password('test-password')
                db.session.add(user)
            db.session.add(donor)
            db.session.flush()
            task = VolunteerTask(
                volunteer_id=volunteer.id,
                task_type='pickup',
                donor_id=donor.id,
                item_name=f'Rice {unique_id}',
                category='Food',
                unit='kg',
                expected_quantity=5
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id
            donor_id = donor.id
            volunteer_email = volunteer.email
            other_email = other_volunteer.email
            staff_email = staff.email

        login_response = self.client.post('/api/auth/login', json={
            'email': volunteer_email,
            'password': 'test-password',
            'role': 'volunteer'
        })
        self.assertEqual(login_response.status_code, 200)
        skipped = self.client.post(f'/api/volunteer-tasks/{task_id}/status', json={'status': 'Picked Up'})
        self.assertEqual(skipped.status_code, 409)
        gps_before_acceptance = self.client.post(
            f'/api/volunteer-tasks/{task_id}/location',
            json={'action': 'start', 'latitude': 12.97, 'longitude': 77.59}
        )
        self.assertEqual(gps_before_acceptance.status_code, 409)
        tasks_response = self.client.get('/api/volunteer-tasks')
        self.assertEqual(tasks_response.status_code, 200)
        self.assertEqual(tasks_response.get_json()['tasks'][0]['donor_address'], 'Private pickup address')

        accepted = self.client.post(f'/api/volunteer-tasks/{task_id}/status', json={'status': 'Accepted'})
        self.assertEqual(accepted.status_code, 200)
        on_the_way = self.client.post(f'/api/volunteer-tasks/{task_id}/status', json={'status': 'On the Way'})
        self.assertEqual(on_the_way.status_code, 200)

        location_response = self.client.post(
            f'/api/volunteer-tasks/{task_id}/location',
            json={'action': 'start', 'latitude': 12.97, 'longitude': 77.59, 'accuracy_meters': 8}
        )
        self.assertEqual(location_response.status_code, 200)
        self.assertTrue(location_response.get_json()['task']['location_sharing'])
        stop_response = self.client.post(
            f'/api/volunteer-tasks/{task_id}/location', json={'action': 'stop'}
        )
        self.assertEqual(stop_response.status_code, 200)

        picked_up = self.client.post(f'/api/volunteer-tasks/{task_id}/status', json={'status': 'Picked Up'})
        self.assertEqual(picked_up.status_code, 200)
        complete_response = self.client.post(
            f'/api/volunteer-tasks/{task_id}/status', json={'status': 'Returned', 'quantity': 4}
        )
        self.assertEqual(complete_response.status_code, 200)
        with self.app.app_context():
            donation = Donation.query.filter_by(donor_id=donor_id).order_by(Donation.id.desc()).first()
            self.assertEqual(donation.quantity, 4)
            stock = InventoryItem.query.filter_by(name=f'Rice {unique_id}', category='Food').first()
            self.assertEqual(stock.quantity, 4)

        staff_client = self.app.test_client()
        staff_login = staff_client.post('/api/auth/login', json={
            'email': staff_email,
            'password': 'test-password',
            'role': 'staff'
        })
        self.assertEqual(staff_login.status_code, 200)
        staff_tasks = staff_client.get('/api/volunteer-tasks').get_json()['tasks']
        self.assertTrue(any(task['id'] == task_id and task['status'] == 'Returned' for task in staff_tasks))

        other_client = self.app.test_client()
        other_login = other_client.post('/api/auth/login', json={
            'email': other_email,
            'password': 'test-password',
            'role': 'volunteer'
        })
        self.assertEqual(other_login.status_code, 200)
        self.assertEqual(other_client.get('/api/volunteer-tasks').get_json()['tasks'], [])
        self.assertEqual(other_client.post(
            f'/api/volunteer-tasks/{task_id}/location', json={'action': 'stop'}
        ).status_code, 403)

    def test_assigned_delivery_updates_stock_and_distribution_history(self):
        unique_id = uuid.uuid4().hex
        with self.app.app_context():
            volunteer = User(name='Delivery Volunteer', email=f'delivery-{unique_id}@example.test', role='volunteer')
            staff = User(name='Delivery Staff', email=f'delivery-staff-{unique_id}@example.test', role='staff')
            volunteer.set_password('test-password')
            staff.set_password('test-password')
            beneficiary = Beneficiary(name='Delivery Recipient', location='North district', eligibility_category='Emergency Relief')
            inventory_item = InventoryItem(name=f'Blankets {unique_id}', category='Clothes', quantity=10, unit='items')
            db.session.add_all([volunteer, staff, beneficiary, inventory_item])
            db.session.commit()
            volunteer_id = volunteer.id
            volunteer_email = volunteer.email
            staff_email = staff.email
            beneficiary_id = beneficiary.id
            inventory_item_id = inventory_item.id

        staff_client = self.app.test_client()
        staff_login = staff_client.post('/api/auth/login', json={
            'email': staff_email,
            'password': 'test-password',
            'role': 'staff'
        })
        self.assertEqual(staff_login.status_code, 200)
        task_response = staff_client.post('/api/volunteer-tasks', json={
            'task_type': 'delivery',
            'volunteer_id': volunteer_id,
            'beneficiary_id': beneficiary_id,
            'inventory_item_id': inventory_item_id,
            'expected_quantity': 3
        })
        self.assertEqual(task_response.status_code, 201)
        task_id = task_response.get_json()['task']['id']

        volunteer_client = self.app.test_client()
        volunteer_login = volunteer_client.post('/api/auth/login', json={
            'email': volunteer_email,
            'password': 'test-password',
            'role': 'volunteer'
        })
        self.assertEqual(volunteer_login.status_code, 200)
        accepted = volunteer_client.post(f'/api/volunteer-tasks/{task_id}/status', json={'status': 'Accepted'})
        self.assertEqual(accepted.status_code, 200)
        out_for_delivery = volunteer_client.post(
            f'/api/volunteer-tasks/{task_id}/status', json={'status': 'Out for Delivery'}
        )
        self.assertEqual(out_for_delivery.status_code, 200)
        completion = volunteer_client.post(f'/api/volunteer-tasks/{task_id}/status', json={
            'status': 'Delivered', 'quantity': 3
        })
        self.assertEqual(completion.status_code, 200)

        with self.app.app_context():
            self.assertEqual(db.session.get(InventoryItem, inventory_item_id).quantity, 7)
            self.assertTrue(Distribution.query.filter_by(beneficiary_id=beneficiary_id).first())

    def test_volunteer_accepts_assigned_task_and_updates_status(self):
        unique_id = uuid.uuid4().hex
        with self.app.app_context():
            volunteer = User(name='Status Volunteer', email=f'status-{unique_id}@example.test', role='volunteer')
            volunteer.set_password('test-password')
            donor = Donor(name='Status Donor', email=f'status-donor-{unique_id}@example.test', address='Pickup Road')
            db.session.add_all([volunteer, donor])
            db.session.flush()
            task = VolunteerTask(
                volunteer_id=volunteer.id,
                task_type='pickup',
                donor_id=donor.id,
                item_name='Food box',
                category='Food',
                unit='boxes',
                expected_quantity=2
            )
            db.session.add(task)
            db.session.commit()
            volunteer_email = volunteer.email
            task_id = task.id

        login_response = self.client.post('/api/auth/login', json={
            'email': volunteer_email,
            'password': 'test-password',
            'role': 'volunteer'
        })
        self.assertEqual(login_response.status_code, 200)
        response = self.client.post(f'/api/volunteer-tasks/{task_id}/status', json={'status': 'Accepted'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['task']['status'], 'Accepted')

    def test_volunteer_can_access_donor_personal_info_and_gps_location(self):
        unique_id = uuid.uuid4().hex
        with self.app.app_context():
            volunteer = User(name='Tracking Volunteer', email=f'tracker-{unique_id}@example.test', role='volunteer')
            volunteer.set_password('test-password')
            donor = Donor(
                name='Generous Donor',
                email=f'generous-{unique_id}@example.test',
                phone='555-9876',
                address='123 Hope St, Sector 9',
                preferred_causes='Disaster Relief'
            )
            db.session.add_all([volunteer, donor])
            db.session.flush()

            task = VolunteerTask(
                volunteer_id=volunteer.id,
                task_type='pickup',
                donor_id=donor.id,
                item_name='First Aid Kits',
                category='Medical',
                unit='boxes',
                expected_quantity=10
            )
            db.session.add(task)
            db.session.commit()
            volunteer_email = volunteer.email
            task_id = task.id
            donor_id = donor.id

        volunteer_client = self.app.test_client()
        login_res = volunteer_client.post('/api/auth/login', json={
            'email': volunteer_email,
            'password': 'test-password',
            'role': 'volunteer'
        })
        self.assertEqual(login_res.status_code, 200)

        accepted = volunteer_client.post(f'/api/volunteer-tasks/{task_id}/status', json={'status': 'Accepted'})
        self.assertEqual(accepted.status_code, 200)

        # 1. Access task and verify donor personal information payload
        tasks_res = volunteer_client.get('/api/volunteer-tasks')
        self.assertEqual(tasks_res.status_code, 200)
        task_data = tasks_res.get_json()['tasks'][0]
        self.assertEqual(task_data['donor_name'], 'Generous Donor')
        self.assertEqual(task_data['donor_email'], f'generous-{unique_id}@example.test')
        self.assertEqual(task_data['donor_phone'], '555-9876')
        self.assertEqual(task_data['donor_address'], '123 Hope St, Sector 9')
        self.assertEqual(task_data['donor_preferred_causes'], 'Disaster Relief')

        # 2. Access donor profile route
        donor_res = volunteer_client.get(f'/api/donors/{donor_id}')
        self.assertEqual(donor_res.status_code, 200)
        self.assertEqual(donor_res.get_json()['donor']['name'], 'Generous Donor')

        # 3. Access GPS location tracking and history
        loc_start = volunteer_client.post(
            f'/api/volunteer-tasks/{task_id}/location',
            json={'action': 'start', 'latitude': 13.0827, 'longitude': 80.2707, 'accuracy_meters': 5.0}
        )
        self.assertEqual(loc_start.status_code, 200)

        loc_get = volunteer_client.get(f'/api/volunteer-tasks/{task_id}/location')
        self.assertEqual(loc_get.status_code, 200)
        loc_json = loc_get.get_json()
        self.assertTrue(loc_json['location_sharing'])
        self.assertEqual(loc_json['latest_location']['latitude'], 13.0827)
        self.assertEqual(len(loc_json['location_history']), 1)


if __name__ == '__main__':
    unittest.main()
