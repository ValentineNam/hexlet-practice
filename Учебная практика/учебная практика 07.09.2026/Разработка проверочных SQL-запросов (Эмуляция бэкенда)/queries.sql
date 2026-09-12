-- =====================================================
-- 1. Список партнеров с количеством доставок
-- =====================================================
SELECT
    p.partner_id,
    p.company_name,
    p.contact_email,
    COUNT(sh.sale_id) AS total_shipments
FROM partners AS p
LEFT JOIN sales_history AS sh
    ON sh.partner_id = p.partner_id
GROUP BY
    p.partner_id,
    p.company_name,
    p.contact_email
ORDER BY p.company_name ASC;

-- =====================================================
-- 2. Транзакция: добавление нового партнера
--    и первой тестовой доставки в одном блоке
-- =====================================================
BEGIN;

-- Создаем новый тестовый продукт, если его еще нет
INSERT INTO products (product_id, product_name)
VALUES (4, 'Тестовый продукт для проверки')
ON CONFLICT (product_id) DO NOTHING;

-- Создаем нового партнера
INSERT INTO partners (partner_id, company_name, inn, contact_email, phone, rating)
VALUES (4, 'ООО "Тестовый партнер"', '1234567890', 'test_partner@example.com', '+79000000000', 4.7)
ON CONFLICT (partner_id) DO NOTHING;

-- Создаем первую тестовую доставку этого партнера
INSERT INTO sales_history (sale_id, partner_id, product_id, sale_date, quantity, total_amount)
VALUES (106, 4, 4, '2026-09-12', 25, 12500.00)
ON CONFLICT (sale_id) DO NOTHING;

COMMIT;

-- =====================================================
-- 3. История отгрузок конкретного партнера за период
--    Пример: партнер с ID = 2, период: 2026-03-01 ... 2026-03-31
-- =====================================================
SELECT
    sh.sale_id,
    sh.sale_date,
    p.product_name,
    sh.quantity,
    sh.total_amount
FROM sales_history AS sh
JOIN products AS p
    ON p.product_id = sh.product_id
WHERE sh.partner_id = 2
  AND sh.sale_date BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'
ORDER BY sh.sale_date ASC, sh.sale_id ASC;

-- =====================================================
-- Дополнительный пример для другого партнера:
-- SELECT ... WHERE sh.partner_id = 1 AND sh.sale_date BETWEEN ... ;
-- =====================================================
