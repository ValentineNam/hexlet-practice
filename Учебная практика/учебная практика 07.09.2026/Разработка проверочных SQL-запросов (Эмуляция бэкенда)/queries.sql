-- =====================================================
-- 1. Список партнеров с количеством отгрузок
-- =====================================================
SELECT
    p.partner_id,
    p.company_name,
    p.contact_email,
    COUNT(s.shipment_id) AS total_shipments
FROM partners AS p
LEFT JOIN shipments AS s
    ON s.partner_id = p.partner_id
GROUP BY
    p.partner_id,
    p.company_name,
    p.contact_email
ORDER BY p.company_name ASC;

-- =====================================================
-- 2. Транзакция: добавление нового партнера и его первой отгрузки
-- =====================================================
BEGIN;

INSERT INTO partners (partner_id, company_name, inn, contact_email, phone, rating)
VALUES (4, 'ООО "Тестовый партнер"', '1234567890', 'test_partner@example.com', '+79000000000', 4.7)
ON CONFLICT (partner_id) DO NOTHING;

INSERT INTO shipments (shipment_id, partner_id, shipment_date, total_amount)
VALUES (105, 4, '2026-09-12', 2500.00)
ON CONFLICT (shipment_id) DO NOTHING;

INSERT INTO shipment_items (shipment_item_id, shipment_id, product_id, quantity, unit_price, line_total)
VALUES (5, 105, 1, 5, 500.0000, 2500.00)
ON CONFLICT (shipment_item_id) DO NOTHING;

COMMIT;

-- =====================================================
-- 3. История отгрузок конкретного партнера за период
--    Пример: партнер с ID = 2, период: 2026-03-01 ... 2026-03-31
-- =====================================================
SELECT
    s.shipment_id,
    s.shipment_date,
    pr.product_name,
    si.quantity,
    si.unit_price,
    si.line_total
FROM shipments AS s
JOIN shipment_items AS si
    ON si.shipment_id = s.shipment_id
JOIN products AS pr
    ON pr.product_id = si.product_id
WHERE s.partner_id = 2
  AND s.shipment_date BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
ORDER BY s.shipment_date ASC, s.shipment_id ASC;

-- =====================================================
-- Альтернативный запрос по одному конкретному партнеру и товару
-- =====================================================
-- SELECT
--     s.shipment_id,
--     s.shipment_date,
--     pr.product_name,
--     si.quantity,
--     si.line_total
-- FROM shipments s
-- JOIN shipment_items si ON si.shipment_id = s.shipment_id
-- JOIN products pr ON pr.product_id = si.product_id
-- WHERE s.partner_id = 1
--   AND pr.product_name = 'Стиральный порошок "Альфа"';
