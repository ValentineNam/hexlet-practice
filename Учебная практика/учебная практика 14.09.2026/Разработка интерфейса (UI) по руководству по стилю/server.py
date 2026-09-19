import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = None
for candidate in ROOT_DIR.iterdir():
    if 'Интеграция с БД' in candidate.name:
        BACKEND_DIR = candidate
        break

if BACKEND_DIR is not None:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    env_file = BACKEND_DIR / '.env' if BACKEND_DIR is not None else None
    if env_file and env_file.exists():
        load_dotenv(env_file)

import psycopg2
from psycopg2.extras import RealDictCursor

from discount_service import calculate_partner_discount

STATIC_DIR = Path(__file__).resolve().parent


def get_db_connection():
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ.get('DB_NAME', 'practice_2026_autumn'),
        user=os.environ.get('DB_USER', 'v.nam'),
        password=os.environ.get('DB_PASSWORD', ''),
        connect_timeout=5,
    )


def build_logo(company_name: str, partner_id: int):
    letter = next((ch for ch in company_name if ch.isalpha()), 'П')
    letter = letter.upper()

    shapes = ['circle', 'square', 'diamond']
    palettes = [
        {'bg': '#f0f0f0', 'color': '#2d2d2d'},
        {'bg': '#1a1a1a', 'color': '#f5f5f5'},
        {'bg': '#d9d9d9', 'color': '#1e1e1e'},
    ]

    shape = shapes[partner_id % len(shapes)]
    palette = palettes[partner_id % len(palettes)]

    return {
        'shape': shape,
        'letter': letter,
        'color': palette['color'],
        'bg': palette['bg'],
    }


def get_partners():
    query = """
        SELECT
            p.partner_id,
            p.company_name,
            p.phone,
            p.contact_email,
            COALESCE(SUM(si.quantity), 0) AS total_quantity
        FROM partners AS p
        LEFT JOIN shipments AS s
            ON s.partner_id = p.partner_id
        LEFT JOIN shipment_items AS si
            ON si.shipment_id = s.shipment_id
        GROUP BY p.partner_id, p.company_name, p.phone, p.contact_email
        ORDER BY p.partner_id;
    """

    try:
        with get_db_connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
    except Exception as exc:  # pragma: no cover
        print(f'Ошибка получения партнеров: {exc}')
        return []

    result = []
    for row in rows:
        total_quantity = int(row.get('total_quantity') or 0)
        discount = calculate_partner_discount(total_quantity)

        result.append({
            'id': int(row['partner_id']),
            'company_name': row['company_name'],
            'director': 'Директор',
            'phone': row['phone'],
            'email': row['contact_email'],
            'discount': discount,
            'logo': build_logo(row['company_name'], int(row['partner_id'])),
        })

    return result


class PartnerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        if self.path == '/api/partners':
            payload = json.dumps(get_partners()).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(payload)
            return

        return super().do_GET()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8000'))
    server = ThreadingHTTPServer(('127.0.0.1', port), PartnerHandler)
    print(f'Сервер запущен на http://127.0.0.1:{port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nСервер остановлен.')
    finally:
        server.server_close()
