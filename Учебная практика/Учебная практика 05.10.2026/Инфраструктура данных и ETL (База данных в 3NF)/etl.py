import csv
import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
RAW_DIR = ROOT_DIR / 'raw'
REJECTIONS_PATH = ROOT_DIR / 'etl_rejections.csv'
SCHEMA_NAME = 'practice_2026_10_05'
PRACTICE_ROOT = ROOT_DIR.parent.parent
PREVIOUS_PRACTICE = next(
    (path for path in PRACTICE_ROOT.iterdir() if path.is_dir() and '14.09.2026' in path.name),
    None,
)
PREVIOUS_BACKEND = next(
    (path for path in PREVIOUS_PRACTICE.iterdir() if path.is_dir() and 'Интеграция с БД' in path.name),
    None,
) if PREVIOUS_PRACTICE is not None else None
DATE_FORMATS = (
    '%d.%m.%Y',
    '%Y/%m/%d',
    '%Y-%m-%d',
    '%d-%m-%Y',
    '%Y.%m.%d',
)
PARTNER_TYPE_PATTERN = re.compile(r'^(ООО|АО|ЗАО|ПАО|ИП)\b', re.IGNORECASE)
LATIN_INITIALS_PATTERN = re.compile(r'\b([A-Z])\.\s*([A-Z])\.(?=$|\s)')
LATIN_TO_CYRILLIC_INITIALS = {'A': 'А', 'B': 'В'}


def read_csv(path, encoding):
    with path.open('r', encoding=encoding, newline='') as source:
        return list(csv.DictReader(source))


def clean_text(value):
    return ' '.join((value or '').strip().split())


def clean_partner_name(value):
    name = clean_text(value)
    name = name.replace('...', '')
    name = clean_text(name)
    name = LATIN_INITIALS_PATTERN.sub(
        lambda match: (
            f"{LATIN_TO_CYRILLIC_INITIALS.get(match.group(1), match.group(1))}."
            f"{LATIN_TO_CYRILLIC_INITIALS.get(match.group(2), match.group(2))}."
        ),
        name,
    )
    return name


def detect_partner_type(name):
    match = PARTNER_TYPE_PATTERN.match(name)
    if match is None:
        return None
    return match.group(1).upper()


def remove_partner_type(name):
    return clean_text(PARTNER_TYPE_PATTERN.sub('', name, count=1))


def parse_date(value):
    cleaned_value = clean_text(value)
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned_value, date_format).date()
        except ValueError:
            continue
    raise ValueError(f'неподдерживаемый формат даты: {cleaned_value!r}')


def parse_decimal(value, field_name):
    try:
        amount = Decimal(clean_text(value))
    except InvalidOperation as error:
        raise ValueError(f'поле {field_name} не является числом: {value!r}') from error
    if not amount.is_finite() or amount < 0:
        raise ValueError(f'поле {field_name} должно быть конечным числом не меньше 0')
    return amount.quantize(Decimal('0.01'))


def transform_sources(raw_dir=RAW_DIR):
    rejections = []
    partners = []
    products = []
    sales = []

    raw_partners = read_csv(raw_dir / 'partners_raw.csv', 'utf-8-sig')
    partner_ids = set()
    partner_inns = set()
    partner_emails = set()

    for row_number, row in enumerate(raw_partners, start=2):
        try:
            partner_id = int(clean_text(row['partner_id']))
            full_partner_name = clean_partner_name(row['partner_name'])
            partner_type = detect_partner_type(full_partner_name)
            company_name = remove_partner_type(full_partner_name)
            inn = clean_text(row['inn'])
            email = clean_text(row['email']).lower()
            if partner_id in partner_ids:
                raise ValueError(f'повторный partner_id={partner_id}')
            if not company_name:
                raise ValueError('пустое наименование партнера')
            if partner_type is None:
                raise ValueError(f'не удалось определить тип партнера: {company_name!r}')
            if not re.fullmatch(r'\d{10,12}', inn):
                raise ValueError(f'некорректный ИНН: {inn!r}')
            if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
                raise ValueError(f'некорректный email: {email!r}')
            if inn in partner_inns:
                raise ValueError(f'повторный ИНН: {inn}')
            if email in partner_emails:
                raise ValueError(f'повторный email: {email}')
            partners.append((partner_id, company_name, partner_type, inn, email))
            partner_ids.add(partner_id)
            partner_inns.add(inn)
            partner_emails.add(email)
        except (KeyError, ValueError) as error:
            rejections.append(('partners_raw.csv', row_number, str(error)))

    raw_products = read_csv(raw_dir / 'products_raw.csv', 'cp1251')
    product_ids = set()
    product_prices = {}

    for row_number, row in enumerate(raw_products, start=2):
        try:
            product_id = int(clean_text(row['product_id']))
            product_name = clean_text(row['product_name'])
            list_price = parse_decimal(row['price'], 'price')
            if product_id in product_ids:
                raise ValueError(f'повторный product_id={product_id}')
            if not product_name:
                raise ValueError('пустое наименование продукта')
            if any(product_name == existing[1] for existing in products):
                raise ValueError(f'повторное наименование продукта: {product_name}')
            products.append((product_id, product_name, list_price))
            product_ids.add(product_id)
            product_prices[product_id] = list_price
        except (KeyError, ValueError) as error:
            rejections.append(('products_raw.csv', row_number, str(error)))

    raw_sales = read_csv(raw_dir / 'sales_history_raw.csv', 'utf-8-sig')
    sale_ids = set()

    for row_number, row in enumerate(raw_sales, start=2):
        try:
            sale_id = int(clean_text(row['sale_id']))
            partner_id = int(clean_text(row['partner_id']))
            product_id = int(clean_text(row['product_id']))
            sale_date = parse_date(row['sale_date'])
            quantity = int(clean_text(row['quantity']))
            amount = parse_decimal(row['amount'], 'amount')
            if sale_id in sale_ids:
                raise ValueError(f'повторный sale_id={sale_id}')
            if partner_id not in partner_ids:
                raise ValueError(f'битый внешний ключ partner_id={partner_id}')
            if product_id not in product_prices:
                raise ValueError(f'битый внешний ключ product_id={product_id}')
            if quantity <= 0:
                raise ValueError(f'quantity должен быть больше 0, получено {quantity}')
            expected_amount = product_prices[product_id] * quantity
            if amount != expected_amount:
                raise ValueError(
                    f'amount={amount} не совпадает с quantity * list_price={expected_amount}'
                )
            unit_price = amount / quantity
            sales.append((sale_id, partner_id, product_id, sale_date, quantity, unit_price))
            sale_ids.add(sale_id)
        except (KeyError, ValueError) as error:
            rejections.append(('sales_history_raw.csv', row_number, str(error)))

    return partners, products, sales, rejections


def write_rejections(rejections, output_path=REJECTIONS_PATH):
    with output_path.open('w', encoding='utf-8', newline='') as report:
        writer = csv.writer(report)
        writer.writerow(('source_file', 'source_row', 'reason'))
        writer.writerows(rejections)


def get_connection():
    schema_name = os.environ.get('DB_SCHEMA', SCHEMA_NAME)
    if schema_name != SCHEMA_NAME:
        raise ValueError(f'DB_SCHEMA must be {SCHEMA_NAME!r} for this import.')
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ.get('DB_NAME', 'practice_2026_autumn'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', ''),
        connect_timeout=5,
    )


def run_etl():
    partners, products, sales, rejections = transform_sources()
    schema_sql = (ROOT_DIR / 'schema.sql').read_text(encoding='utf-8')

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(schema_sql)
            cursor.execute('TRUNCATE sales_history, products, partners')
            cursor.executemany(
                '''
                INSERT INTO partners (partner_id, company_name, partner_type, inn, contact_email)
                VALUES (%s, %s, %s, %s, %s)
                ''',
                partners,
            )
            cursor.executemany(
                '''
                INSERT INTO products (product_id, product_name, list_price)
                VALUES (%s, %s, %s)
                ''',
                products,
            )
            cursor.executemany(
                '''
                INSERT INTO sales_history (
                    sale_id, partner_id, product_id, sale_date, quantity, unit_price_at_sale
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ''',
                sales,
            )
            cursor.execute('SELECT COUNT(*) FROM partners')
            partners_count = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM products')
            products_count = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM sales_history')
            sales_count = cursor.fetchone()[0]
            cursor.execute(
                '''
                SELECT COUNT(*)
                FROM sales_history AS sh
                LEFT JOIN partners AS p ON p.partner_id = sh.partner_id
                LEFT JOIN products AS pr ON pr.product_id = sh.product_id
                WHERE p.partner_id IS NULL OR pr.product_id IS NULL
                '''
            )
            broken_foreign_keys = cursor.fetchone()[0]

    write_rejections(rejections)
    print(f'partners imported: {partners_count}')
    print(f'products imported: {products_count}')
    print(f'sales imported: {sales_count}')
    print(f'rows rejected: {len(rejections)} ({REJECTIONS_PATH.name})')
    print(f'broken foreign keys after import: {broken_foreign_keys}')


if __name__ == '__main__':
    load_dotenv(ROOT_DIR / '.env')
    if PREVIOUS_BACKEND is not None:
        load_dotenv(PREVIOUS_BACKEND / '.env', override=False)
    run_etl()
