BEGIN TRANSACTION READ ONLY;
SET LOCAL search_path TO practice_2026_10_05;

-- Counts информационные: пользовательские записи могут увеличивать значения.
SELECT 'partners' AS table_name, count(*) AS row_count FROM partners
UNION ALL SELECT 'products', count(*) FROM products
UNION ALL SELECT 'sales_history', count(*) FROM sales_history
UNION ALL SELECT 'product_types', count(*) FROM product_types
UNION ALL SELECT 'material_types', count(*) FROM material_types;

-- Все invalid_count должны быть равны нулю.
SELECT * FROM data_quality_checks ORDER BY check_name;

-- Следующие выборки должны быть пустыми сразу после импорта исходного набора.
-- После ручного редактирования они показывают расхождение с CSV, а не обязательно ошибку БД.
WITH expected(partner_id, company_name, partner_type, inn, contact_email) AS (
    VALUES (1, '"Вектор"', 'ООО', '7701234567', 'vector@mail.ru'),
           (2, 'Петров А.В.', 'ИП', '7802345678', 'petrov@yandex.ru'),
           (3, '"Технолоджис"', 'АО', '5003456789', 'info@techno.ru'),
           (4, '"Альфа"', 'ООО', '7704567890', 'alpha@gmail.com'),
           (5, 'Сидоров И.И.', 'ИП', '7805678901', 'sidorov@llc.ru')
)
SELECT * FROM expected
EXCEPT SELECT partner_id, company_name, partner_type, inn, contact_email FROM partners;

WITH expected(product_id, product_name, list_price) AS (
    VALUES (101, 'Ноутбук Pro', 75000.00), (102, 'Смартфон X', 45000.50), (103, 'Монитор 27"', 18200.00)
)
SELECT * FROM expected EXCEPT SELECT product_id, product_name, list_price FROM products;

WITH expected(sale_id, partner_id, product_id, sale_date, quantity, sale_amount) AS (
    VALUES (1001, 1, 101, DATE '2023-10-25', 2, 150000.00),
           (1002, 2, 102, DATE '2023-10-26', 1, 45000.50),
           (1004, 4, 103, DATE '2023-10-28', 10, 182000.00),
           (1005, 3, 102, DATE '2023-10-29', 3, 135001.50),
           (1006, 5, 103, DATE '2023-10-30', 1, 18200.00)
)
SELECT * FROM expected EXCEPT SELECT sale_id, partner_id, product_id, sale_date, quantity, sale_amount FROM sales_history;

SELECT * FROM sales_history WHERE sale_id = 1003 AND partner_id = 999;
SELECT (SELECT last_value + CASE WHEN is_called THEN 1 ELSE 0 END FROM partners_partner_id_seq)
       > COALESCE(max(partner_id), 0) AS next_partner_id_is_free FROM partners;
SELECT product_type_id, coefficient, data_source FROM product_types ORDER BY product_type_id;
SELECT material_type_id, scrap_percentage, data_source FROM material_types ORDER BY material_type_id;
COMMIT;
