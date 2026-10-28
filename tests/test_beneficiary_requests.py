import uuid
import unittest

from app import create_app
from database import db
from models.beneficiary import Beneficiary
from models.user import User


class BeneficiaryRequestTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_beneficiary_can_register_and_submit_request_visible_to_staff(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        unique_id = uuid.uuid4().hex
        response = self.client.post('/api/auth/register', json={
            'name': 'Test Beneficiary',
            'email': f'beneficiary-{unique_id}@example.test',
            'password': 'test-password',
            'phone': '5551234567',
            'role': 'beneficiary',
            'location': 'North District',
            'eligibility_category': 'Emergency Relief'
        })
        self.assertEqual(response.status_code, 201)
        user_data = response.get_json()['user']
        self.assertEqual(user_data['role'], 'beneficiary')

        profile_response = self.client.get('/api/beneficiaries')
        self.assertEqual(profile_response.status_code, 200)
        profile = profile_response.get_json()['beneficiaries'][0]
        self.assertEqual(profile['name'], 'Test Beneficiary')
        self.assertEqual(profile['status'], 'Pending')

        request_response = self.client.post('/api/beneficiaries/requests', json={
            'category': 'Food',
            'description': 'Need a food package this week',
            'urgency': 'High'
        })
        self.assertEqual(request_response.status_code, 201)
        aid_request_id = request_response.get_json()['request']['id']
        self.assertEqual(self.client.put(
            f'/api/beneficiaries/requests/{aid_request_id}', json={'status': 'Approved'}
        ).status_code, 403)

        with self.app.app_context():
            staff = User(name='Review Staff', email=f'reviewer-{unique_id}@example.test', role='staff')
            staff.set_password('test-password')
            db.session.add(staff)
            db.session.commit()
            staff_email = staff.email

        staff_client = self.app.test_client()
        login_response = staff_client.post('/api/auth/login', json={
            'email': staff_email,
            'password': 'test-password',
            'role': 'staff'
        })
        self.assertEqual(login_response.status_code, 200)
        review_list = staff_client.get('/api/beneficiaries/requests')
        self.assertEqual(review_list.status_code, 200)
        self.assertTrue(any(
            item['beneficiary_name'] == 'Test Beneficiary'
            for item in review_list.get_json()['requests']
        ))
        update_response = staff_client.put(f'/api/beneficiaries/requests/{aid_request_id}', json={
            'status': 'Under Review',
            'staff_note': 'We are checking available supplies.'
        })
        self.assertEqual(update_response.status_code, 200)
        beneficiary_requests = self.client.get('/api/beneficiaries/requests').get_json()['requests']
        self.assertEqual(beneficiary_requests[0]['status'], 'Under Review')
        self.assertEqual(beneficiary_requests[0]['staff_note'], 'We are checking available supplies.')


if __name__ == '__main__':
    unittest.main()
