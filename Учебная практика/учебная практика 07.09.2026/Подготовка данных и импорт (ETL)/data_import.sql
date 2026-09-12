-- =====================================================
-- Data import for 3NF schema
-- =====================================================

-- Вставка партнеров
INSERT INTO partners (partner_id, company_name, inn, contact_email, phone, rating)
OVERRIDING SYSTEM VALUE
VALUES
    (1, 'ООО "Логистик-Экспресс"', '7701234567', 'info@logex.ru', '+79991112233', 4.8),
    (2, 'ИП Петров А.В.', '5001098765', 'petrov_delivery@mail.ru', '+79041112233', 4.2),
    (3, 'ТК "Быстрый Путь"', '7812345678', 'speedway@yandex.ru', '+78125554433', 4.9);

-- Вставка товаров
INSERT INTO products (product_id, product_name)
OVERRIDING SYSTEM VALUE
VALUES
    (1, 'Стиральный порошок "Альфа"'),
    (2, 'Мыло жидкое "Стандарт"'),
    (3, 'Кондиционер для белья');

-- Вставка шапок отгрузок
INSERT INTO shipments (shipment_id, partner_id, shipment_date, total_amount)
OVERRIDING SYSTEM VALUE
VALUES
    (101, 1, '2026-03-01', 25000.00),
    (102, 2, '2026-03-15', 18000.50),
    (103, 1, '2026-03-20', 10500.00),
    (104, 3, '2026-03-25', 13500.00);

-- Вставка строк отгрузок
INSERT INTO shipment_items (shipment_item_id, shipment_id, product_id, quantity, unit_price, line_total)
OVERRIDING SYSTEM VALUE
VALUES
    (1, 101, 1, 50, 500.0000, 25000.00),
    (2, 102, 2, 200, 90.0025, 18000.50),
    (3, 103, 3, 30, 350.0000, 10500.00),
    (4, 104, 2, 150, 90.0000, 13500.00);

-- =====================================================
-- Проверка импорта
-- =====================================================
SELECT COUNT(*) AS partners_count FROM partners;
SELECT COUNT(*) AS products_count FROM products;
SELECT COUNT(*) AS shipments_count FROM shipments;
SELECT COUNT(*) AS shipment_items_count FROM shipment_items;

-- Проверка внешних ключей
SELECT s.shipment_id, s.partner_id
FROM shipments s
LEFT JOIN partners p ON p.partner_id = s.partner_id
WHERE p.partner_id IS NULL;

SELECT si.shipment_item_id, si.product_id
FROM shipment_items si
LEFT JOIN products p ON p.product_id = si.product_id
WHERE p.product_id IS NULL;