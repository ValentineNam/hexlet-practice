from decimal import Decimal, InvalidOperation, ROUND_CEILING
from math import isfinite


# Демонстрационные справочники используются вместо отсутствующих таблиц БД.
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


def calculate_material_requirement(
    product_type_id: int,
    material_type_id: int,
    quantity: int,
    param_1: float,
    param_2: float,
) -> int:
    """Return the required material units, rounded up, or -1 for invalid input."""
    if type(product_type_id) is not int or type(material_type_id) is not int:
        return -1
    if type(quantity) is not int or quantity <= 0:
        return -1
    if not _is_positive_finite_number(param_1):
        return -1
    if not _is_positive_finite_number(param_2):
        return -1

    product_coefficient = PRODUCT_TYPE_COEFFICIENTS.get(product_type_id)
    scrap_percentage = MATERIAL_SCRAP_PERCENTAGES.get(material_type_id)
    if product_coefficient is None or scrap_percentage is None:
        return -1

    try:
        first_parameter = Decimal(str(param_1))
        second_parameter = Decimal(str(param_2))
        scrap_multiplier = Decimal('1') + scrap_percentage / Decimal('100')
        material_amount = (
            first_parameter
            * second_parameter
            * product_coefficient
            * quantity
            * scrap_multiplier
        )
        return int(material_amount.to_integral_value(rounding=ROUND_CEILING))
    except (InvalidOperation, OverflowError, ValueError):
        return -1


def _is_positive_finite_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False

    try:
        return isfinite(value) and value > 0
    except (OverflowError, TypeError, ValueError):
        return False
