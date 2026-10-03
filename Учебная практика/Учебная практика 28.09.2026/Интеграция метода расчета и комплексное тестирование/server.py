import importlib.util
import json
import logging
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
PRACTICE_ROOT = ROOT_DIR.parent.parent
CALCULATOR_DIR = ROOT_DIR.parent / 'Разработка ядра алгоритма расчета материалов'

if not (CALCULATOR_DIR / 'material_calculator.py').is_file():
    raise RuntimeError('Не найден модуль расчета материалов предыдущего задания.')

sys.path.insert(0, str(CALCULATOR_DIR))
calculator_spec = importlib.util.spec_from_file_location(
    'material_calculator',
    CALCULATOR_DIR / 'material_calculator.py',
)
calculator = importlib.util.module_from_spec(calculator_spec)
sys.modules[calculator_spec.name] = calculator
calculator_spec.loader.exec_module(calculator)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)


def calculate_from_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError('Ожидался JSON-объект с параметрами расчета.')

    required_fields = (
        'product_type_id',
        'material_type_id',
        'quantity',
        'param_1',
        'param_2',
    )
    if any(field not in payload for field in required_fields):
        raise ValueError('Передайте все пять параметров расчета.')

    return calculator.calculate_material_requirement(
        payload['product_type_id'],
        payload['material_type_id'],
        payload['quantity'],
        payload['param_1'],
        payload['param_2'],
    )


class CalculatorHandler(SimpleHTTPRequestHandler):
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
        if self.path == '/api/material/catalogs':
            return self.send_json(200, {
                'product_types': [
                    {'id': identifier, 'coefficient': str(coefficient)}
                    for identifier, coefficient in calculator.PRODUCT_TYPE_COEFFICIENTS.items()
                ],
                'material_types': [
                    {'id': identifier, 'scrap_percentage': str(percentage)}
                    for identifier, percentage in calculator.MATERIAL_SCRAP_PERCENTAGES.items()
                ],
            })
        return super().do_GET()

    def do_POST(self):
        if self.path != '/api/material/calculate':
            return self.send_json(404, {'error': 'Маршрут не найден.'})

        try:
            content_length = int(self.headers.get('Content-Length', '0'))
            payload = json.loads(self.rfile.read(content_length))
            amount = calculate_from_payload(payload)
            return self.send_json(200, {'material_requirement': amount})
        except (ValueError, json.JSONDecodeError) as error:
            return self.send_json(400, {'error': str(error)})
        except Exception:
            logging.exception('Ошибка при расчете расхода материала')
            return self.send_json(500, {'error': 'Внутренняя ошибка расчета.'})

    def log_message(self, format_string, *args):
        logging.info('%s - %s', self.address_string(), format_string % args)


if __name__ == '__main__':
    import os

    port = int(os.environ.get('PORT', '8008'))
    http_server = ThreadingHTTPServer(('127.0.0.1', port), CalculatorHandler)
    print(f'CRM: Расчет расхода материала — http://127.0.0.1:{port}')
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped.')
    finally:
        http_server.server_close()
