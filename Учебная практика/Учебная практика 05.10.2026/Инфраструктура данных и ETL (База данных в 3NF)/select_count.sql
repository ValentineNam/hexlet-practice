SET search_path TO practice_2026_10_05;

SELECT 'partners' AS table_name, COUNT(*) AS row_count FROM partners
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'sales_history', COUNT(*) FROM sales_history;

SELECT sh.sale_id, sh.partner_id, sh.product_id
FROM sales_history AS sh
LEFT JOIN partners AS p ON p.partner_id = sh.partner_id
LEFT JOIN products AS pr ON pr.product_id = sh.product_id
WHERE p.partner_id IS NULL OR pr.product_id IS NULL;

SELECT sale_id, sale_date
FROM sales_history
WHERE sale_date IS NULL;
