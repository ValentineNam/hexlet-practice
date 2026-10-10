"""Чтение справочников; никакого fallback на демонстрационные данные."""

from contextlib import closing

import psycopg2

from database import get_db_connection


class CatalogUnavailableError(RuntimeError):
    pass


def get_coefficients(product_type_id, material_type_id):
    try:
        with closing(get_db_connection()) as connection:
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """SELECT p.coefficient, m.scrap_percentage
                           FROM product_types p CROSS JOIN material_types m
                           WHERE p.product_type_id = %s AND m.material_type_id = %s""",
                        (product_type_id, material_type_id),
                    )
                    return cursor.fetchone()
    except (psycopg2.Error, ValueError) as error:
        raise CatalogUnavailableError('Справочники недоступны. Проверьте подключение и импорт данных.') from error


def list_catalogs():
    try:
        with closing(get_db_connection()) as connection:
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT product_type_id, coefficient, data_source FROM product_types ORDER BY product_type_id')
                    products = cursor.fetchall()
                    cursor.execute('SELECT material_type_id, scrap_percentage, data_source FROM material_types ORDER BY material_type_id')
                    materials = cursor.fetchall()
        if not products or not materials:
            raise CatalogUnavailableError('Справочники пусты. Выполните импорт данных.')
        return {
            'product_types': [{'id': key, 'coefficient': str(value), 'data_source': source} for key, value, source in products],
            'material_types': [{'id': key, 'scrap_percentage': str(value), 'data_source': source} for key, value, source in materials],
        }
    except (psycopg2.Error, ValueError) as error:
        raise CatalogUnavailableError('Справочники недоступны. Проверьте подключение и импорт данных.') from error
