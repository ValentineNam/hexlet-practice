-- Запросы для подсчета количества записей в таблицах
SELECT COUNT(*) AS partners_count FROM partners;
SELECT COUNT(*) AS products_count FROM products;
SELECT COUNT(*) AS sales_count FROM sales_history;

-- Запросы для проверки ссылочной целостности
SELECT s.sale_id, s.partner_id
FROM sales_history s
LEFT JOIN partners p ON p.partner_id = s.partner_id
WHERE p.partner_id IS NULL;

SELECT s.sale_id, s.product_id
FROM sales_history s
LEFT JOIN products p ON p.product_id = s.product_id
WHERE p.product_id IS NULL;