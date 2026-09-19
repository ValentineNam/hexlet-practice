# Интеграция с БД и агрегация данных

## Описание

В этом задании реализован пример интеграции Python с PostgreSQL и расчета скидки на основе суммарного объёма товаров партнера.

В проекте используется нормализованная 3NF-модель:
- `partners`
- `shipments`
- `shipment_items`

Это соответствует текущей схеме, в которой данные по продажам хранятся в таблицах `shipments` и `shipment_items`, а не в одном денормализованном `sales_history`.

## Что реализовано

- подключение к PostgreSQL через `psycopg2`
- SQL-запрос с `LEFT JOIN` и `SUM(quantity)`
- функция расчета скидки по суммарному количеству товаров
- словарь/объект результата, который включает данные партнера и его текущую скидку

## Основной файл

- `backend_integration.py`

## SQL-логика

Запрос агрегирует суммарное количество по партнеру:

```sql
SELECT
    p.partner_id,
    p.company_name,
    p.contact_email,
    COALESCE(SUM(si.quantity), 0) AS total_quantity
FROM partners AS p
LEFT JOIN shipments AS s
    ON s.partner_id = p.partner_id
LEFT JOIN shipment_items AS si
    ON si.shipment_id = s.shipment_id
WHERE p.partner_id = %s
GROUP BY p.partner_id, p.company_name, p.contact_email;
```

## Формула скидки

```python
if total_quantity < 10000:
    return 0
if 10000 <= total_quantity <= 49999:
    return 5
if 50000 <= total_quantity <= 299999:
    return 10
return 15
```

## Как запустить

1. Установите зависимости:

```bash
pip install psycopg2-binary
```

2. Проверьте, что PostgreSQL запущен, и укажите параметры подключения через переменные окружения:

```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=postgres
export DB_USER=postgres
export DB_PASSWORD=postgres
```

3. Запустите скрипт:

```bash
python3 backend_integration.py
```

## Пример результата

```python
{
    'partner_id': 2,
    'company_name': 'ООО "Партнер 2"',
    'contact_email': 'partner2@example.com',
    'total_quantity': 125000,
    'discount_percent': 10
}
```

## Примечание

Если у вас уже есть другая структура базы данных, поправьте SQL-запрос и параметры подключения под вашу среду.
