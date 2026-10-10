import importlib.util
import json
import logging
import os
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

ROOT_DIR = Path(__file__).resolve().parent
PRACTICE_ROOT = ROOT_DIR.parent.parent
OCTOBER_TASKS = PRACTICE_ROOT / 'Учебная практика 05.10.2026'
ETL_DIR = OCTOBER_TASKS / 'Инфраструктура данных и ETL (База данных в 3NF)'
LOGIC_DIR = OCTOBER_TASKS / 'Реализация ядра бизнес-логики (Расчеты и алгоритмы)'
PREVIOUS_BACKEND = (
    PRACTICE_ROOT
    / 'Учебная практика 21.09.2026'
    / 'Интеграция формы с БД (CRUD-операции и обновление UI)'
)
PREVIOUS_PRACTICE = next(
    (path for path in PRACTICE_ROOT.iterdir() if path.is_dir() and '14.09.2026' in path.name),
    None,
)
SEPTEMBER_BACKEND = next(
    (
        path
        for path in PREVIOUS_PRACTICE.iterdir()
        if path.is_dir() and 'Интеграция с БД' in path.name
    ),
    None,
) if PREVIOUS_PRACTICE is not None else None

load_dotenv(ETL_DIR / '.env')
load_dotenv(PREVIOUS_BACKEND / '.env', override=False)
if SEPTEMBER_BACKEND is not None:
    load_dotenv(SEPTEMBER_BACKEND / '.env', override=False)


def load_module(module_name, module_path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


discount_module = load_module('october_discount', LOGIC_DIR / 'discount.py')
material_module = load_module('october_material_calculator', LOGIC_DIR / 'material_calculator.py')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(ROOT_DIR / 'app.log', encoding='utf-8'),
        logging.StreamHandler(),
    ],
)

PARTNER_TYPES = {'ООО', 'АО', 'ЗАО', 'ПАО', 'ИП'}
PARTNER_FIELDS = (
    'company_name',
    'partner_type',
    'inn',
    'rating',
    'address',
    'director',
    'phone',
    'email',
)


def get_db_connection():
    schema_name = os.environ.get('DB_SCHEMA', 'practice_2026_10_05')
    if not re.fullmatch(r'[a-z_][a-z0-9_]*', schema_name):
        raise ValueError('DB_SCHEMA must be a lowercase SQL identifier.')

    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ.get('DB_NAME', 'practice_2026_autumn'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', ''),
        connect_timeout=5,
        options=f'-c search_path={schema_name}',
    )


def validate_partner(payload):
    if not isinstance(payload, dict):
        raise ValueError('Ожидался JSON-объект с данными партнера.')

    partner = {field: payload.get(field) for field in PARTNER_FIELDS}
    partner['company_name'] = str(partner['company_name'] or '').strip()
    partner['partner_type'] = str(partner['partner_type'] or '').strip().upper()
    partner['inn'] = str(partner['inn'] or '').strip()
    partner['address'] = str(partner['address'] or '').strip()
    partner['director'] = str(partner['director'] or '').strip()
    partner['phone'] = str(partner['phone'] or '').strip()
    partner['email'] = str(partner['email'] or '').strip().lower()

    if not partner['company_name']:
        raise ValueError('Укажите наименование партнера.')
    if partner['partner_type'] not in PARTNER_TYPES:
        raise ValueError('Выберите корректный тип партнера.')
    if not re.fullmatch(r'\d{10}|\d{12}', partner['inn']):
        raise ValueError('ИНН должен содержать 10 или 12 цифр.')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', partner['email']):
        raise ValueError('Укажите корректный email.')

    try:
        rating = int(partner['rating'])
    except (TypeError, ValueError) as error:
        raise ValueError('Рейтинг должен быть целым числом от 0 до 5.') from error

    if isinstance(partner['rating'], bool) or str(partner['rating']).strip() != str(rating):
        raise ValueError('Рейтинг должен быть целым числом от 0 до 5.')
    if rating < 0 or rating > 5:
        raise ValueError('Рейтинг должен быть целым числом от 0 до 5.')

    partner['rating'] = rating
    partner['phone'] = partner['phone'] or None
    partner['address'] = partner['address'] or None
    partner['director'] = partner['director'] or None
    return partner


def build_logo(company_name, partner_id):
    letter = next((character for character in company_name if character.isalpha()), 'П').upper()
    shapes = ('circle', 'square', 'diamond')
    palettes = (
        {'bg': '#f0e6d2', 'color': '#542f25'},
        {'bg': '#315c51', 'color': '#fffaf0'},
        {'bg': '#d5a64b', 'color': '#202823'},
    )
    position = partner_id % len(shapes)
    return {
        'shape': shapes[position],
        'letter': letter,
        'color': palettes[position]['color'],
        'bg': palettes[position]['bg'],
    }


def serialize_partner(row):
    partner = dict(row)
    total_quantity = int(partner.pop('total_quantity') or 0)
    partner['id'] = int(partner.pop('partner_id'))
    partner['rating'] = int(partner['rating']) if partner['rating'] is not None else 0
    partner['discount'] = discount_module.calculate_partner_discount(total_quantity)
    partner['logo'] = build_logo(partner['company_name'], partner['id'])
    return partner


def list_partners():
    query = '''
        SELECT
            p.partner_id,
            p.company_name,
            p.partner_type,
            p.inn,
            p.rating,
            p.address,
            p.director,
            p.phone,
            p.contact_email AS email,
            COALESCE(SUM(sh.quantity), 0) AS total_quantity
        FROM partners AS p
        LEFT JOIN sales_history AS sh ON sh.partner_id = p.partner_id
        GROUP BY p.partner_id
        ORDER BY p.partner_id
    '''
    with get_db_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            return [serialize_partner(row) for row in cursor.fetchall()]


def get_partner(partner_id):
    query = '''
        SELECT partner_id, company_name, partner_type, inn, rating,
               address, director, phone, contact_email AS email
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
    partner['rating'] = int(partner['rating']) if partner['rating'] is not None else 0
    return partner


def get_partner_history(partner_id):
    partner = get_partner(partner_id)
    if partner is None:
        return None

    query = '''
        SELECT pr.product_name, sh.quantity,
               TO_CHAR(sh.sale_date, 'DD.MM.YYYY') AS sale_date
        FROM sales_history AS sh
        JOIN products AS pr ON pr.product_id = sh.product_id
        WHERE sh.partner_id = %s
        ORDER BY sh.sale_date DESC, sh.sale_id DESC
    '''
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (partner_id,))
            history = cursor.fetchall()

    return {
        'partner': partner,
        'rows': [
            {'product_name': row[0], 'quantity': int(row[1]), 'sale_date': row[2]}
            for row in history
        ],
    }


def save_partner(partner_id, payload):
    partner = validate_partner(payload)
    values = tuple(partner[field] for field in PARTNER_FIELDS)

    if partner_id is None:
        query = '''
            INSERT INTO partners (
                company_name, partner_type, inn, rating, address,
                director, phone, contact_email
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING partner_id
        '''
    else:
        query = '''
            UPDATE partners
            SET company_name = %s, partner_type = %s, inn = %s, rating = %s,
                address = %s, director = %s, phone = %s, contact_email = %s
            WHERE partner_id = %s
            RETURNING partner_id
        '''
        values += (partner_id,)

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, values)
            row = cursor.fetchone()

    return row[0] if row else None


def read_json(handler):
    try:
        length = int(handler.headers.get('Content-Length', '0'))
        return json.loads(handler.rfile.read(length))
    except (ValueError, json.JSONDecodeError) as error:
        raise ValueError('Тело запроса должно содержать корректный JSON.') from error


class AppHandler(SimpleHTTPRequestHandler):
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
            return self.run_api(list_partners)

        history_match = re.fullmatch(r'/api/partners/(\d+)/history', path)
        if history_match:
            return self.run_api(lambda: get_partner_history(int(history_match.group(1))), True)

        partner_match = re.fullmatch(r'/api/partners/(\d+)', path)
        if partner_match:
            return self.run_api(lambda: get_partner(int(partner_match.group(1))), True)

        if path == '/api/material/catalogs':
            return self.send_json(200, {
                'product_types': [
                    {'id': key, 'coefficient': str(value)}
                    for key, value in material_module.PRODUCT_TYPE_COEFFICIENTS.items()
                ],
                'material_types': [
                    {'id': key, 'scrap_percentage': str(value)}
                    for key, value in material_module.MATERIAL_SCRAP_PERCENTAGES.items()
                ],
            })

        self.path = path
        return super().do_GET()

    def do_POST(self):
        if self.path == '/api/material/calculate':
            try:
                payload = read_json(self)
                required = ('product_type_id', 'material_type_id', 'quantity', 'param_1', 'param_2')
                if not isinstance(payload, dict) or any(field not in payload for field in required):
                    raise ValueError('Передайте все пять параметров расчета.')
                result = material_module.calculate_material_requirement(*(payload[field] for field in required))
                return self.send_json(200, {'material_requirement': result})
            except ValueError as error:
                return self.send_json(400, {'error': str(error)})
            except Exception:
                logging.exception('Ошибка расчета расхода материала')
                return self.send_json(500, {'error': 'Внутренняя ошибка расчета материала.'})

        if self.path != '/api/partners':
            return self.send_json(404, {'error': 'Маршрут не найден.'})

        try:
            partner_id = save_partner(None, read_json(self))
            return self.send_json(201, {'id': partner_id})
        except ValueError as error:
            return self.send_json(400, {'error': str(error)})
        except psycopg2.IntegrityError:
            logging.exception('Нарушение ограничения при создании партнера')
            return self.send_json(409, {'error': 'ИНН или email уже используется.'})
        except Exception:
            logging.exception('Ошибка создания партнера')
            return self.send_json(500, {'error': 'Не удалось сохранить партнера. Проверьте подключение к БД.'})

    def do_PUT(self):
        match = re.fullmatch(r'/api/partners/(\d+)', urlparse(self.path).path)
        if match is None:
            return self.send_json(404, {'error': 'Маршрут не найден.'})
        try:
            partner_id = save_partner(int(match.group(1)), read_json(self))
            if partner_id is None:
                return self.send_json(404, {'error': 'Партнер не найден.'})
            return self.send_json(200, {'id': partner_id})
        except ValueError as error:
            return self.send_json(400, {'error': str(error)})
        except psycopg2.IntegrityError:
            logging.exception('Нарушение ограничения при обновлении партнера')
            return self.send_json(409, {'error': 'ИНН или email уже используется.'})
        except Exception:
            logging.exception('Ошибка обновления партнера')
            return self.send_json(500, {'error': 'Не удалось обновить партнера. Проверьте подключение к БД.'})

    def run_api(self, operation, not_found=False):
        try:
            result = operation()
            if not_found and result is None:
                return self.send_json(404, {'error': 'Партнер не найден.'})
            return self.send_json(200, result)
        except Exception:
            logging.exception('Ошибка чтения данных приложения')
            return self.send_json(500, {'error': 'Не удалось загрузить данные. Проверьте базу данных.'})

    def log_message(self, format_string, *args):
        logging.info('%s - %s', self.address_string(), format_string % args)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8010'))
    http_server = ThreadingHTTPServer(('127.0.0.1', port), AppHandler)
    print(f'CRM final app: http://127.0.0.1:{port}')
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped.')
    finally:
        http_server.server_close()
