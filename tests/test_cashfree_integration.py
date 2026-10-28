import unittest

from app import create_app


class CashfreeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_cashfree_config_endpoint_reports_disabled_without_keys(self):
        self.app.config['CASHFREE_APP_ID'] = ''
        self.app.config['CASHFREE_SECRET_KEY'] = ''

        response = self.client.get('/api/donations/cashfree/config')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {
            'enabled': False,
            'environment': 'sandbox'
        })


if __name__ == '__main__':
    unittest.main()
