from decimal import Decimal, DecimalException, ROUND_CEILING, localcontext

from material_catalogs import get_coefficients


def calculate_material_requirement(
    product_type_id: int,
    material_type_id: int,
    quantity: int,
    param_1: float,
    param_2: float,
) -> int:
    """Некорректные данные -> -1; сбой БД -> CatalogUnavailableError."""
    if any(type(value) is not int or not 0 < value <= 2147483647
           for value in (product_type_id, material_type_id)):
        return -1
    if type(quantity) is not int or quantity <= 0:
        return -1
    parameters = []
    for value in (param_1, param_2):
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            return -1
        try:
            number = Decimal(str(value))
            if not number.is_finite() or number <= 0:
                return -1
            parameters.append(number)
        except (DecimalException, ValueError):
            return -1

    coefficients = get_coefficients(product_type_id, material_type_id)
    if coefficients is None:
        return -1
    coefficient, defect_percent = coefficients
    try:
        numbers = [*parameters, Decimal(quantity), coefficient, defect_percent]
        # Запас точности сохраняет дробный хвост до ceil даже за пределами 28 цифр.
        with localcontext() as context:
            context.prec = sum(len(n.as_tuple().digits) + abs(n.as_tuple().exponent) for n in numbers) + 10
            amount = parameters[0] * parameters[1] * quantity * coefficient * (1 + defect_percent / 100)
            return int(amount.to_integral_value(rounding=ROUND_CEILING))
    except (DecimalException, OverflowError, ValueError):
        return -1
