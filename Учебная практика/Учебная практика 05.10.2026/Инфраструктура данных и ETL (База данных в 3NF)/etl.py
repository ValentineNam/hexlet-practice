import argparse
import csv
import importlib.util
import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql

from validation import MAX_INTEGER, clean_text, validate_partner

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


def parse_positive_integer(value, field_name):
    number = int(clean_text(value))
    if not 0 < number <= MAX_INTEGER:
        raise ValueError(f'{field_name}: ожидается целое от 1 до {MAX_INTEGER}')
    return number


def parse_decimal(value, field_name, maximum=Decimal('9999999999.99')):
    try:
        amount = Decimal(clean_text(value))
        if not amount.is_finite() or not 0 <= amount <= maximum:
            raise ValueError(f'{field_name}: сумма вне допустимого диапазона')
        rounded = amount.quantize(Decimal('0.01'))
        if rounded != amount:
            raise ValueError(f'{field_name}: допускается не более двух знаков после запятой')
        return rounded
    except InvalidOperation as error:
        raise ValueError(f'{field_name}: некорректная сумма') from error


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
            partner_id = parse_positive_integer(row['partner_id'], 'partner_id')
            full_partner_name = clean_partner_name(row['partner_name'])
            partner_type = detect_partner_type(full_partner_name)
            company_name = remove_partner_type(full_partner_name)
            inn = clean_text(row['inn'])
            email = clean_text(row['email']).lower()
            if partner_id in partner_ids:
                raise ValueError(f'повторный partner_id={partner_id}')
            normalized = validate_partner({
                'company_name': company_name,
                'partner_type': partner_type,
                'inn': inn,
                'email': email,
                'rating': 0,
            })
            company_name = normalized['company_name']
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

    for row_number, row in enumerate(raw_products, start=2):
        try:
            product_id = parse_positive_integer(row['product_id'], 'product_id')
            product_name = clean_text(row['product_name'])
            list_price = parse_decimal(row['price'], 'price')
            if product_id in product_ids:
                raise ValueError(f'повторный product_id={product_id}')
            if not product_name or len(product_name) > 255:
                raise ValueError('наименование продукта: от 1 до 255 символов')
            if any(product_name == existing[1] for existing in products):
                raise ValueError(f'повторное наименование продукта: {product_name}')
            products.append((product_id, product_name, list_price))
            product_ids.add(product_id)
        except (KeyError, ValueError) as error:
            rejections.append(('products_raw.csv', row_number, str(error)))

    raw_sales = read_csv(raw_dir / 'sales_history_raw.csv', 'utf-8-sig')
    sale_ids = set()

    for row_number, row in enumerate(raw_sales, start=2):
        try:
            sale_id = parse_positive_integer(row['sale_id'], 'sale_id')
            partner_id = parse_positive_integer(row['partner_id'], 'partner_id')
            product_id = parse_positive_integer(row['product_id'], 'product_id')
            sale_date = parse_date(row['sale_date'])
            quantity = parse_positive_integer(row['quantity'], 'quantity')
            amount = parse_decimal(row['amount'], 'amount', Decimal('99999999999999999999.99'))
            if sale_id in sale_ids:
                raise ValueError(f'повторный sale_id={sale_id}')
            if partner_id not in partner_ids:
                raise ValueError(f'битый внешний ключ partner_id={partner_id}')
            if product_id not in product_ids:
                raise ValueError(f'битый внешний ключ product_id={product_id}')
            # CSV содержит сумму продажи, а не обязательно текущую прайс-листовую цену.
            sales.append((sale_id, partner_id, product_id, sale_date, quantity, amount))
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


TABLE_COLUMNS = {
    'partners': ('partner_id', 'company_name', 'partner_type', 'inn', 'contact_email'),
    'products': ('product_id', 'product_name', 'list_price'),
    'sales_history': ('sale_id', 'partner_id', 'product_id', 'sale_date', 'quantity', 'sale_amount'),
    'product_types': ('product_type_id', 'coefficient', 'data_source'),
    'material_types': ('material_type_id', 'scrap_percentage', 'data_source'),
}


def load_demo_catalogs():
    module_path = (
        ROOT_DIR.parent / 'Реализация ядра бизнес-логики (Расчеты и алгоритмы)'
        / 'material_calculator.py'
    )
    spec = importlib.util.spec_from_file_location('etl_demo_materials', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {
        'product_types': [(key, value, 'demo') for key, value in module.PRODUCT_TYPE_COEFFICIENTS.items()],
        'material_types': [(key, value, 'demo') for key, value in module.MATERIAL_SCRAP_PERCENTAGES.items()],
    }


def merge_rows(cursor, table, rows):
    """Добавляет только отсутствующие строки; конфликт отменяет всю загрузку."""
    columns = TABLE_COLUMNS[table]
    fields = sql.SQL(', ').join(map(sql.Identifier, columns))
    select_query = sql.SQL('SELECT {} FROM {} WHERE {} = %s').format(
        fields, sql.Identifier(table), sql.Identifier(columns[0]),
    )
    insert_query = sql.SQL('INSERT INTO {} ({}) VALUES ({})').format(
        sql.Identifier(table), fields,
        sql.SQL(', ').join(sql.Placeholder() for _ in columns),
    )
    inserted = 0
    for row in rows:
        cursor.execute(select_query, (row[0],))
        existing = cursor.fetchone()
        if existing is not None:
            if tuple(existing) != tuple(row):
                raise ValueError(
                    f'Конфликт {table}, ID={row[0]}: существующая запись отличается. '
                    'Данные не перезаписаны; транзакция отменена.'
                )
            continue
        cursor.execute(insert_query, row)
        inserted += 1
    return inserted


def verify_rows(cursor, table, expected_rows):
    columns = TABLE_COLUMNS[table]
    query = sql.SQL('SELECT {} FROM {} WHERE {} = %s').format(
        sql.SQL(', ').join(map(sql.Identifier, columns)),
        sql.Identifier(table), sql.Identifier(columns[0]),
    )
    for expected in expected_rows:
        cursor.execute(query, (expected[0],))
        actual = cursor.fetchone()
        if actual is None or tuple(actual) != tuple(expected):
            raise ValueError(f'Проверка загрузки не пройдена: {table}, ID={expected[0]}')


def run_etl(raw_dir=RAW_DIR, output_path=REJECTIONS_PATH):
    partners, products, sales, rejections = transform_sources(raw_dir)
    datasets = {'partners': partners, 'products': products, 'sales_history': sales}
    datasets.update(load_demo_catalogs())
    schema_sql = (ROOT_DIR / 'schema.sql').read_text(encoding='utf-8')
    # Ошибка записи отчета должна произойти до изменения БД.
    write_rejections(rejections, output_path)
    connection = get_connection()
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(schema_sql)
                cursor.execute(
                    'LOCK TABLE partners, products, sales_history, product_types, material_types '
                    'IN SHARE ROW EXCLUSIVE MODE'
                )
                stats = {}
                for table, rows in datasets.items():
                    inserted = merge_rows(cursor, table, rows)
                    verify_rows(cursor, table, rows)
                    stats[table] = {'inserted': inserted, 'unchanged': len(rows) - inserted}
                cursor.execute((ROOT_DIR / 'sync_partner_sequence.sql').read_text(encoding='utf-8'))
                cursor.execute('SELECT check_name, invalid_count FROM data_quality_checks WHERE invalid_count <> 0')
                failures = cursor.fetchall()
                if failures:
                    raise ValueError(f'Проверки целостности не пройдены: {failures}')
    finally:
        connection.close()
    for table, counts in stats.items():
        print(f'{table}: added={counts["inserted"]}, unchanged={counts["unchanged"]}')
    print(f'rows rejected: {len(rejections)} ({output_path})')
    return stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Безопасный импорт без удаления и перезаписи записей.')
    parser.add_argument('--check-only', action='store_true', help='Проверить CSV без подключения к БД и записи отчета.')
    args = parser.parse_args()
    if args.check_only:
        partners, products, sales, rejections = transform_sources()
        print(f'partners={len(partners)}, products={len(products)}, sales={len(sales)}')
        print(f'rejections={rejections}')
    else:
        load_dotenv(ROOT_DIR / '.env')
        if PREVIOUS_BACKEND is not None:
            load_dotenv(PREVIOUS_BACKEND / '.env', override=False)
        run_etl()
