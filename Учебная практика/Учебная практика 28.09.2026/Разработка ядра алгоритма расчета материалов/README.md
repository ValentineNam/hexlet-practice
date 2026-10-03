# Разработка ядра алгоритма расчета материалов

## Реализовано

Модуль `material_calculator.py` содержит функцию:

```python
calculate_material_requirement(
    product_type_id: int,
    material_type_id: int,
    quantity: int,
    param_1: float,
    param_2: float,
) -> int
```

Расчет выполняется по формуле:

```text
ceil(quantity * param_1 * param_2 * product_type_coefficient * (1 + material_scrap_percent / 100))
```

Для воспроизводимого изолированного ядра используются мок-справочники `PRODUCT_TYPE_COEFFICIENTS` и `MATERIAL_SCRAP_PERCENTAGES`. Значения в них демонстрационные, поскольку конкретные коэффициенты не заданы в требованиях и соответствующих справочников пока нет в схеме БД. Их можно заменить загрузкой данных из БД при интеграции.

Функция возвращает `-1` при неизвестном ID, некорректных/нецелых ID и количестве, `quantity <= 0`, неположительных или нечисловых параметрах, а также `NaN`/бесконечности. Успешный результат округляется вверх до целого.

## Использование

Из этой папки:

```bash
python3 - <<'PY'
from material_calculator import calculate_material_requirement

amount = calculate_material_requirement(1, 2, 100, 1.0, 1.0)
print(amount)
PY
```

## Тесты

```bash
python3 -m unittest discover -s tests -v
```

Набор покрывает обычный расчет, округление вверх, неизвестные ID, неположительные размеры и количество, нечисловые/неfinite значения и неверные типы аргументов.
