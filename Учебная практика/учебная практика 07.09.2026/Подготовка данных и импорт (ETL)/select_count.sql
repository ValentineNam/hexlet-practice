-- Запросы для подсчета количества записей в таблицах
SELECT COUNT(*) AS partners_count FROM partners;
SELECT COUNT(*) AS products_count FROM products;
SELECT COUNT(*) AS shipments_count FROM shipments;
SELECT COUNT(*) AS shipment_items_count FROM shipment_items;

-- Запросы для проверки ссылочной целостности
SELECT s.shipment_id, s.partner_id
FROM shipments s
LEFT JOIN partners p ON p.partner_id = s.partner_id
WHERE p.partner_id IS NULL;

SELECT si.shipment_item_id, si.product_id
FROM shipment_items si
LEFT JOIN products p ON p.product_id = si.product_id
WHERE p.product_id IS NULL;