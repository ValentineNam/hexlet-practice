import json
import logging
import os
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

ROOT_DIR = Path(__file__).resolve().parent
PRACTICE_ROOT = ROOT_DIR.parent.parent
PREVIOUS_PRACTICE = next(
    (path for path in PRACTICE_ROOT.iterdir() if '14.09.2026' in path.name),
    None,
)
BACKEND_DIR = next(
    (
        path
        for path in PREVIOUS_PRACTICE.iterdir()
        if 'Интеграция с БД' in path.name
    ),
    None,
) if PREVIOUS_PRACTICE is not None else None

load_dotenv(ROOT_DIR / '.env')

if BACKEND_DIR is not None:
    load_dotenv(BACKEND_DIR / '.env', override=False)
    sys.path.insert(0, str(BACKEND_DIR))

from discount_service import calculate_partner_discount

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)

PARTNER_FIELDS = (
    'company_name',
    'partner_type',
    'rating',
    'address',
    'director',
    'phone',
    'inn',
    'email',
)


def get_db_connection():
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ.get('DB_NAME', 'practice_2026_autumn'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', ''),
        connect_timeout=5,
    )


def validate_partner(payload):
    if not isinstance(payload, dict):
        raise ValueError('Ожидался объект с данными партнера.')

    partner = {field: payload.get(field) for field in PARTNER_FIELDS}
    partner['company_name'] = str(partner['company_name'] or '').strip()
    partner['email'] = str(partner['email'] or '').strip()
    partner['inn'] = str(partner['inn'] or '').strip()
    partner['partner_type'] = str(partner['partner_type'] or '').strip()
    partner['address'] = str(partner['address'] or '').strip()
    partner['director'] = str(partner['director'] or '').strip()
    partner['phone'] = str(partner['phone'] or '').strip()

    if not partner['company_name']:
        raise ValueError('Укажите наименование партнера.')
    if not partner['email']:
        raise ValueError('Укажите email компании.')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', partner['email']):
        raise ValueError('Проверьте формат email компании.')
    if not re.fullmatch(r'\d{10}|\d{12}', partner['inn']):
        raise ValueError('ИНН должен содержать 10 или 12 цифр.')
    if partner['partner_type'] not in {'ООО', 'АО', 'ЗАО', 'ИП', 'ПАО'}:
        raise ValueError('Выберите тип партнера из списка.')

    try:
        rating = int(partner['rating'])
    except (TypeError, ValueError) as exc:
        raise ValueError('Рейтинг должен быть целым числом от 0 до 5.') from exc

    if isinstance(partner['rating'], bool) or str(partner['rating']).strip() != str(rating):
        raise ValueError('Рейтинг должен быть целым числом от 0 до 5.')
    if rating < 0 or rating > 5:
        raise ValueError('Рейтинг должен быть целым числом от 0 до 5.')

    partner['rating'] = rating
    return partner


def build_logo(company_name, partner_id):
    letter = next((character for character in company_name if character.isalpha()), 'П').upper()
    shapes = ('circle', 'square', 'diamond')
    palettes = (
        {'bg': '#f0e6d2', 'color': '#542f25'},
        {'bg': '#315c51', 'color': '#fffaf0'},
        {'bg': '#d5a64b', 'color': '#202823'},
    )
    index = partner_id % len(shapes)
    return {
        'shape': shapes[index],
        'letter': letter,
        'color': palettes[index]['color'],
        'bg': palettes[index]['bg'],
    }


def serialize_partner(row):
    partner = dict(row)
    partner['id'] = int(partner.pop('partner_id'))
    partner['rating'] = int(partner['rating'])
    partner['discount'] = calculate_discount(partner.pop('total_quantity'))
    partner['logo'] = build_logo(partner['company_name'], partner['id'])
    return partner


def calculate_discount(total_quantity):
    return calculate_partner_discount(int(total_quantity or 0))


def list_partners():
    query = '''
        SELECT
            p.partner_id,
            p.company_name,
            p.partner_type,
            p.rating,
            p.address,
            p.director,
            p.phone,
            p.inn,
            p.contact_email AS email,
            COALESCE(SUM(si.quantity), 0) AS total_quantity
        FROM partners AS p
        LEFT JOIN shipments AS s ON s.partner_id = p.partner_id
        LEFT JOIN shipment_items AS si ON si.shipment_id = s.shipment_id
        GROUP BY p.partner_id
        ORDER BY p.partner_id
    '''

    with get_db_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            return [serialize_partner(row) for row in cursor.fetchall()]


def get_partner(partner_id):
    query = '''
        SELECT
            partner_id,
            company_name,
            partner_type,
            rating,
            address,
            director,
            phone,
            inn,
            contact_email AS email
        FROM partners
        WHERE partner_id = %s
    '''

    with get_db_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (partner_id,))
            row = cursor.fetchone()

    if row is None:
        return None

    partner = dict(row)
    partner['id'] = int(partner.pop('partner_id'))
    partner['rating'] = int(partner['rating'])
    return partner


def create_partner(payload):
    partner = validate_partner(payload)
    query = '''
        INSERT INTO partners (
            company_name, partner_type, rating, address, director, phone, inn, contact_email
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING partner_id
    '''
    values = tuple(partner[field] for field in PARTNER_FIELDS)

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, values)
            partner_id = cursor.fetchone()[0]

    return partner_id


def update_partner(partner_id, payload):
    partner = validate_partner(payload)
    query = '''
        UPDATE partners
        SET company_name = %s,
            partner_type = %s,
            rating = %s,
            address = %s,
            director = %s,
            phone = %s,
            inn = %s,
            contact_email = %s
        WHERE partner_id = %s
        RETURNING partner_id
    '''
    values = tuple(partner[field] for field in PARTNER_FIELDS) + (partner_id,)

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, values)
            row = cursor.fetchone()

    return row[0] if row else None


def read_json(handler):
    try:
        length = int(handler.headers.get('Content-Length', '0'))
        return json.loads(handler.rfile.read(length))
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError('Тело запроса должно содержать корректный JSON.') from exc


class PartnerHandler(SimpleHTTPRequestHandler):
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
            return self.handle_api(list_partners)

        match = re.fullmatch(r'/api/partners/(\d+)', path)
        if match:
            partner_id = int(match.group(1))
            return self.handle_api(lambda: get_partner(partner_id), not_found=True)

        self.path = path
        return super().do_GET()

    def do_POST(self):
        if self.path != '/api/partners':
            return self.send_json(404, {'error': 'Маршрут не найден.'})

        try:
            partner_id = create_partner(read_json(self))
            return self.send_json(201, {'id': partner_id})
        except ValueError as exc:
            return self.send_json(400, {'error': str(exc)})
        except psycopg2.IntegrityError as exc:
            logging.exception('Не удалось создать партнера из-за ограничения БД')
            message = 'Такой email или ИНН уже используется.'
            return self.send_json(409, {'error': message})
        except Exception:
            logging.exception('Ошибка создания партнера')
            return self.send_json(500, {'error': 'Не удалось сохранить партнера. Проверьте подключение к БД.'})

    def do_PUT(self):
        match = re.fullmatch(r'/api/partners/(\d+)', urlparse(self.path).path)
        if not match:
            return self.send_json(404, {'error': 'Маршрут не найден.'})

        partner_id = int(match.group(1))
        try:
            updated_id = update_partner(partner_id, read_json(self))
            if updated_id is None:
                return self.send_json(404, {'error': 'Партнер не найден.'})
            return self.send_json(200, {'id': updated_id})
        except ValueError as exc:
            return self.send_json(400, {'error': str(exc)})
        except psycopg2.IntegrityError:
            logging.exception('Не удалось обновить партнера из-за ограничения БД')
            return self.send_json(409, {'error': 'Такой email или ИНН уже используется.'})
        except Exception:
            logging.exception('Ошибка обновления партнера')
            return self.send_json(500, {'error': 'Не удалось сохранить изменения. Проверьте подключение к БД.'})

    def handle_api(self, operation, not_found=False):
        try:
            result = operation()
            if not_found and result is None:
                return self.send_json(404, {'error': 'Партнер не найден.'})
            return self.send_json(200, result)
        except Exception:
            logging.exception('Ошибка чтения данных партнеров')
            return self.send_json(500, {'error': 'Не удалось загрузить данные. Проверьте подключение к БД.'})

    def log_message(self, format_string, *args):
        logging.info('%s - %s', self.address_string(), format_string % args)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8005'))
    server = ThreadingHTTPServer(('127.0.0.1', port), PartnerHandler)
    print(f'CRM CRUD API: http://127.0.0.1:{port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped.')
    finally:
        server.server_close()
