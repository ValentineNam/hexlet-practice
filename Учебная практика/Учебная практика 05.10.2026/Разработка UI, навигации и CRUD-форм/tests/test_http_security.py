"""HTTP smoke tests without a PostgreSQL connection."""
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import server


class StaticFileSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.AppHandler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.httpd.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=3)

    def status(self, path, method='GET'):
        try:
            with urlopen(Request(self.base + path, method=method), timeout=3) as response:
                return response.status
        except HTTPError as error:
            return error.code

    def test_public_pages_and_assets(self):
        for path in ('/', '/index.html', '/partner-edit.html', '/history.html',
                     '/calculator.html', '/styles.css', '/app.js', '/favicon.svg'):
            with self.subTest(path=path):
                self.assertEqual(self.status(path), 200)

    def test_private_files_not_served(self):
        for path in ('/server.py', '/app.log', '/.env', '/.gitignore',
                     '/tests/test_app_backend.py', '/README.md', '/requirements.txt',
                     '/%2eenv', '/%2fserver.py', '/index.html/../server.py'):
            with self.subTest(path=path):
                self.assertEqual(self.status(path), 404)
                self.assertEqual(self.status(path, 'HEAD'), 404)


if __name__ == '__main__':
    unittest.main()
