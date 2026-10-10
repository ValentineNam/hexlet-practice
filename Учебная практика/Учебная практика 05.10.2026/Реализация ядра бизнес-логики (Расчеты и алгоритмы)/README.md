# Реализация ядра бизнес-логики (Расчеты и алгоритмы)

## Состав

- `discount.py` — накопительная скидка партнера по общему объему продаж.
- `material_calculator.py` — расчет материала с округлением вверх и возвратом `-1` для некорректных данных.
- `test_discount.py`, `test_material_calculator.py` — unit-тесты обеих функций.

Мок-справочники коэффициентов продукции и процента брака демонстрационные: исходные задания не задают численные значения справочников, а в ETL-схеме 05.10 их нет. Функция принимает оба ID и проверяет их наличие в справочниках.

## Запуск тестов

Из этой папки:

```bash
python3 -m unittest discover -s . -p 'test_*.py' -v
```

## Пример расчета

```python
from material_calculator import calculate_material_requirement

result = calculate_material_requirement(1, 2, 100, 1.0, 1.0)
print(result)
```
