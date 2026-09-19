# Интеграция с БД и агрегация данных

## Описание

В этом задании реализован пример интеграции Python с PostgreSQL и расчета скидки на основе суммарного объёма товаров партнера.

В проекте используется нормализованная 3NF-модель:
- `partners`
- `products`
- `shipments`
- `shipment_items`

Это соответствует реальной схеме, которая сейчас есть в PostgreSQL: таблицы `partners`, `products`, `shipments` и `shipment_items`. Данные по продажам хранятся в таблицах `shipments` и `shipment_items`, а не в одном денормализованном `sales_history`.

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

1. Установите зависимости в виртуальном окружении:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install psycopg2-binary python-dotenv
```

2. Создайте файл `.env` в папке проекта и укажите параметры подключения из PGAdmin, например:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=practice_2026_autumn
DB_USER=v.nam
DB_PASSWORD=
```

> Если у вас другой логин, имя БД или пароль, подставьте их из настроек сервера в PGAdmin.

3. Запустите скрипт:

```bash
python backend_integration.py
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
