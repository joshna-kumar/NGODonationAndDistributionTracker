import unittest
from app import create_app
from database import db
from models.donor import Donor
from models.donation import Donation
from models.user import User


class GPayFlowTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            self.donor_user = User(name='Test Donor', email='donor_test@example.com', role='donor')
            self.donor_user.set_password('password123')
            db.session.add(self.donor_user)
            db.session.flush()

            self.donor = Donor(
                user_id=self.donor_user.id,
                name='Test Donor',
                email='donor_test@example.com',
                preferred_causes='Education',
                total_donated=0.0
            )
            db.session.add(self.donor)
            db.session.commit()
            self.donor_id = self.donor.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_gpay_page_renders_successfully(self):
        response = self.client.get('/gpay?amount=750')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Google Pay', response.data)
        self.assertIn(b'Payment Successful', response.data)

    def test_gpay_checkout_creates_payment_successful_donation(self):
        response = self.client.post('/api/donations/gpay-checkout', json={
            'amount': 1500.0,
            'donor_id': self.donor_id,
            'notes': 'Test GPay Donation',
            'upi_pin': '123456'
        })
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['status'], 'Payment Successful')
        self.assertEqual(data['donation']['amount'], 1500.0)
        self.assertEqual(data['donation']['status'], 'Payment Successful')
        self.assertEqual(data['donation']['category'], 'Money')
        self.assertTrue(data['block_hash'])

        with self.app.app_context():
            donor = Donor.query.get(self.donor_id)
            self.assertEqual(donor.total_donated, 1500.0)
            donation = Donation.query.get(data['donation']['id'])
            self.assertEqual(donation.status, 'Payment Successful')
            self.assertEqual(donation.evidence_status, 'Valid')

    def test_gpay_checkout_requires_positive_amount(self):
        response = self.client.post('/api/donations/gpay-checkout', json={
            'amount': 0,
            'donor_id': self.donor_id
        })
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
