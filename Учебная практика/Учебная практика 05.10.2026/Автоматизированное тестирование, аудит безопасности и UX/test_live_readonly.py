"""Opt-in checks of an existing local HTTP server; never call CRUD writes."""
import concurrent.futures
import json
import os
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen


@unittest.skipUnless(os.environ.get('FINAL_AUDIT_LIVE') == '1', 'Set FINAL_AUDIT_LIVE=1 for read-only HTTP checks')
class LiveReadOnlyTests(unittest.TestCase):
    base = 'http://127.0.0.1:8010'

    def request(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        request = Request(self.base + path, data=data, headers={'Content-Type': 'application/json'})
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def test_list_partner_and_history(self):
        status, partners = self.request('/api/partners')
        self.assertEqual(status, 200)
        self.assertIsInstance(partners, list)
        if partners:
            partner_id = partners[0]['id']
            status, partner = self.request(f'/api/partners/{partner_id}')
            self.assertEqual(status, 200)
            self.assertEqual(partner['id'], partner_id)
            status, history = self.request(f'/api/partners/{partner_id}/history')
            self.assertEqual(status, 200)
            self.assertEqual(history['partner']['id'], partner_id)
            self.assertIsInstance(history['rows'], list)

    def test_catalogs_and_control_calculation(self):
        status, catalogs = self.request('/api/material/catalogs')
        self.assertEqual(status, 200)
        self.assertTrue(catalogs['product_types'])
        self.assertTrue(catalogs['material_types'])
        parameters = dict(product_type_id=1, material_type_id=2, quantity=100, param_1='1', param_2='1')
        self.assertEqual(self.request('/api/material/calculate', parameters), (200, {'material_requirement': 126}))
        self.assertEqual(self.request('/api/material/calculate', parameters | dict(quantity=-1)), (200, {'material_requirement': -1}))
        self.assertEqual(self.request('/api/material/calculate', {})[0], 400)

    def test_bounded_read_load(self):
        paths = ['/api/partners', '/api/material/catalogs'] * 12
        started = time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(self.request, paths))
        self.assertEqual([status for status, _ in results], [200] * 24)
        print(f'\nRead-only load: 24 requests, 4 workers, {time.monotonic() - started:.3f}s, 24 HTTP 200')


if __name__ == '__main__':
    unittest.main()
