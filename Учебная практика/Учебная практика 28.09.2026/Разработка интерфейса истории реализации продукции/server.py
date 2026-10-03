import importlib.util
import json
import logging
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT_DIR = Path(__file__).resolve().parent
PRACTICE_ROOT = ROOT_DIR.parent.parent
CRUD_DIR = next(
    (
        path / 'Интеграция формы с БД (CRUD-операции и обновление UI)'
        for path in PRACTICE_ROOT.iterdir()
        if path.is_dir() and '21.09.2026' in path.name
    ),
    None,
)

if CRUD_DIR is None or not (CRUD_DIR / 'server.py').is_file():
    raise RuntimeError('Не найдена папка backend задания 21.09.2026.')

sys.path.insert(0, str(CRUD_DIR))
backend_spec = importlib.util.spec_from_file_location(
    'partner_crud_backend',
    CRUD_DIR / 'server.py',
)
backend = importlib.util.module_from_spec(backend_spec)
sys.modules[backend_spec.name] = backend
backend_spec.loader.exec_module(backend)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)

HISTORY_QUERY = '''
    SELECT
        pr.product_name,
        si.quantity,
        TO_CHAR(s.shipment_date, 'DD.MM.YYYY') AS sale_date
    FROM partners AS p
    JOIN shipments AS s ON s.partner_id = p.partner_id
    JOIN shipment_items AS si ON si.shipment_id = s.shipment_id
    JOIN products AS pr ON pr.product_id = si.product_id
    WHERE p.partner_id = %s
    ORDER BY s.shipment_date DESC, s.shipment_id DESC, pr.product_name
'''


def get_partner_history(partner_id):
    partner = backend.get_partner(partner_id)
    if partner is None:
        return None

    with backend.get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(HISTORY_QUERY, (partner_id,))
            rows = cursor.fetchall()

    return {
        'partner': partner,
        'rows': [
            {
                'product_name': row[0],
                'quantity': int(row[1]),
                'sale_date': row[2],
            }
            for row in rows
        ],
    }


class HistoryHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT_DIR), **kwargs)

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = unquote(urlparse(self.path).path)

        if path == '/api/partners':
            try:
                return self.send_json(200, backend.list_partners())
            except Exception:
                logging.exception('Не удалось загрузить реестр партнеров')
                return self.send_json(500, {'error': 'Не удалось загрузить партнеров из базы данных.'})

        match = re.fullmatch(r'/api/partners/(\d+)/history', path)
        if match:
            partner_id = int(match.group(1))
            try:
                result = get_partner_history(partner_id)
                if result is None:
                    return self.send_json(404, {'error': 'Партнер не найден.'})
                return self.send_json(200, result)
            except Exception:
                logging.exception('Не удалось загрузить историю партнера %s', partner_id)
                return self.send_json(500, {'error': 'Не удалось загрузить историю реализации.'})

        self.path = path
        return super().do_GET()

    def log_message(self, format_string, *args):
        logging.info('%s - %s', self.address_string(), format_string % args)


if __name__ == '__main__':
    port = int(backend.os.environ.get('PORT', '8007'))
    http_server = ThreadingHTTPServer(('127.0.0.1', port), HistoryHandler)
    print(f'CRM: История реализации продукции — http://127.0.0.1:{port}')
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped.')
    finally:
        http_server.server_close()
