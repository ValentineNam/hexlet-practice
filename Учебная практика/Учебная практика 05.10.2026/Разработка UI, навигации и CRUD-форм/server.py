import importlib.util
import json
import logging
import os
import re
import sys
from decimal import Decimal, InvalidOperation
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

import psycopg2
from psycopg2.extras import RealDictCursor

ROOT_DIR = Path(__file__).resolve().parent
PRACTICE_ROOT = ROOT_DIR.parent.parent
OCTOBER_TASKS = PRACTICE_ROOT / 'Учебная практика 05.10.2026'
ETL_DIR = OCTOBER_TASKS / 'Инфраструктура данных и ETL (База данных в 3NF)'
LOGIC_DIR = OCTOBER_TASKS / 'Реализация ядра бизнес-логики (Расчеты и алгоритмы)'
def load_module(module_name, module_path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(LOGIC_DIR))
import discount as discount_module
import material_calculator as material_module
import material_catalogs
from database import get_db_connection

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(ROOT_DIR / 'app.log', encoding='utf-8'),
        logging.StreamHandler(),
    ],
)

validation_module = load_module('october_validation', ETL_DIR / 'validation.py')
PARTNER_TYPES = validation_module.PARTNER_TYPES
PARTNER_FIELDS = validation_module.PARTNER_FIELDS
validate_partner = validation_module.validate_partner

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
        return json.loads(handler.rfile.read(length), parse_float=Decimal)
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
            return self.run_api(material_catalogs.list_catalogs)

        self.path = path
        return super().do_GET()

    def do_POST(self):
        if self.path == '/api/material/calculate':
            try:
                payload = read_json(self)
                required = ('product_type_id', 'material_type_id', 'quantity', 'param_1', 'param_2')
                if not isinstance(payload, dict) or any(field not in payload for field in required):
                    raise ValueError('Передайте все пять параметров расчета.')
                for field in ('param_1', 'param_2'):
                    if isinstance(payload[field], str):
                        try:
                            payload[field] = Decimal(payload[field])
                        except InvalidOperation:
                            return self.send_json(200, {'material_requirement': -1})
                result = material_module.calculate_material_requirement(*(payload[field] for field in required))
                return self.send_json(200, {'material_requirement': result})
            except material_catalogs.CatalogUnavailableError as error:
                logging.exception('Ошибка справочников')
                return self.send_json(503, {'error': str(error)})
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
        except material_catalogs.CatalogUnavailableError as error:
            logging.exception('Ошибка справочников')
            return self.send_json(503, {'error': str(error)})
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
