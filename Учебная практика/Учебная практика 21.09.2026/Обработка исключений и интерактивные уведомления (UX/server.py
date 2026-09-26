import importlib.util
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
CRUD_DIR = ROOT_DIR.parent / 'Интеграция формы с БД (CRUD-операции и обновление UI)'
load_dotenv(ROOT_DIR / '.env')
sys.path.insert(0, str(CRUD_DIR))

backend_spec = importlib.util.spec_from_file_location(
    'partner_crud_backend',
    CRUD_DIR / 'server.py',
)
backend = importlib.util.module_from_spec(backend_spec)
sys.modules[backend_spec.name] = backend
backend_spec.loader.exec_module(backend)


class NotificationHandler(backend.PartnerHandler):
    def __init__(self, *args, **kwargs):
        SimpleHTTPRequestHandler.__init__(self, *args, directory=str(ROOT_DIR), **kwargs)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8006'))
    http_server = ThreadingHTTPServer(('127.0.0.1', port), NotificationHandler)
    print(f'CRM UX: http://127.0.0.1:{port}')
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped.')
    finally:
        http_server.server_close()
