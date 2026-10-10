from decimal import Decimal


# Только начальные учебные данные ETL; рабочий калькулятор читает PostgreSQL.
PRODUCT_TYPE_COEFFICIENTS = {
    1: Decimal('1.20'),
    2: Decimal('1.50'),
    3: Decimal('0.85'),
}

MATERIAL_SCRAP_PERCENTAGES = {
    1: Decimal('2.5'),
    2: Decimal('5'),
    3: Decimal('1.75'),
}


