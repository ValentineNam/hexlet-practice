-- =====================================================
-- Финальный генератор демо-данных для интерфейса
-- Создает 100 партнеров и распределяет их по 4 уровням скидок:
-- 0%  -> без истории продаж
-- 5%  -> диапазон около 10k..50k
-- 10% -> диапазон около 50k..300k
-- 15% -> диапазон около 300k..
--
-- Скрипт пересоздает набор данных, чтобы демонстрация всегда была стабильной.
-- =====================================================

DO $$
DECLARE
    partner_index INTEGER;
    shipment_count INTEGER;
    shipment_index INTEGER;
    product_index INTEGER;
    total_quantity INTEGER;
    remaining_quantity INTEGER;
    current_shipment_quantity INTEGER;
    qty_1 INTEGER;
    qty_2 INTEGER;
    qty_3 INTEGER;
    unit_price_value NUMERIC(12,4);
    line_total_value NUMERIC(12,2);
    shipment_date_value DATE;
    company_name_text TEXT;
    inn_text TEXT;
    email_text TEXT;
    phone_text TEXT;
    rating_value NUMERIC(3,2);
    new_partner_id INTEGER;
    new_shipment_id INTEGER;
BEGIN
    TRUNCATE TABLE shipment_items, shipments, partners RESTART IDENTITY CASCADE;

    FOR partner_index IN 1..100 LOOP
        company_name_text := 'ООО "Партнер ' || partner_index || '"';
        inn_text := LPAD(CAST((900000000 + partner_index) AS TEXT), 10, '0');
        email_text := 'partner' || partner_index || '@example.ru';

        CASE partner_index % 8
            WHEN 0 THEN phone_text := '+7495' || LPAD(CAST((1000000 + partner_index) AS TEXT), 7, '0');
            WHEN 1 THEN phone_text := '+7812' || LPAD(CAST((1000000 + partner_index) AS TEXT), 7, '0');
            WHEN 2 THEN phone_text := '+7900' || LPAD(CAST((1000000 + partner_index) AS TEXT), 7, '0');
            WHEN 3 THEN phone_text := '+7904' || LPAD(CAST((1000000 + partner_index) AS TEXT), 7, '0');
            WHEN 4 THEN phone_text := '+7911' || LPAD(CAST((1000000 + partner_index) AS TEXT), 7, '0');
            WHEN 5 THEN phone_text := '+7921' || LPAD(CAST((1000000 + partner_index) AS TEXT), 7, '0');
            WHEN 6 THEN phone_text := '+7499' || LPAD(CAST((1000000 + partner_index) AS TEXT), 7, '0');
            ELSE phone_text := '+7909' || LPAD(CAST((1000000 + partner_index) AS TEXT), 7, '0');
        END CASE;

        rating_value := ROUND((0.50 + ((partner_index % 6) * 0.70) + ((partner_index % 4) * 0.15)), 2);

        INSERT INTO partners (company_name, inn, contact_email, phone, rating)
        VALUES (company_name_text, inn_text, email_text, phone_text, rating_value)
        RETURNING partner_id INTO new_partner_id;

        IF partner_index % 7 = 0 THEN
            total_quantity := 0;
        ELSIF partner_index % 7 IN (1, 2) THEN
            total_quantity := 12000 + ((partner_index * 37) % 37000);
        ELSIF partner_index % 7 IN (3, 4) THEN
            total_quantity := 50000 + ((partner_index * 47) % 235000);
        ELSE
            total_quantity := 300000 + ((partner_index * 53) % 300000);
        END IF;

        IF total_quantity > 0 THEN
            shipment_count := 2 + (partner_index % 3);
            remaining_quantity := total_quantity;

            FOR shipment_index IN 1..shipment_count LOOP
                IF shipment_index = shipment_count THEN
                    current_shipment_quantity := remaining_quantity;
                ELSE
                    current_shipment_quantity := remaining_quantity / (shipment_count - shipment_index + 1);
                END IF;

                shipment_date_value := DATE '2026-01-01' + ((partner_index * 11 + shipment_index * 17) % 180);

                INSERT INTO shipments (partner_id, shipment_date, total_amount)
                VALUES (new_partner_id, shipment_date_value, 0)
                RETURNING shipment_id INTO new_shipment_id;

                qty_1 := current_shipment_quantity / 3;
                qty_2 := current_shipment_quantity / 3;
                qty_3 := current_shipment_quantity - qty_1 - qty_2;

                FOR product_index IN 1..3 LOOP
                    IF product_index = 1 THEN
                        unit_price_value := 250 + ((partner_index + product_index) % 180);
                        line_total_value := unit_price_value * qty_1;
                        INSERT INTO shipment_items (shipment_id, product_id, quantity, unit_price, line_total)
                        VALUES (new_shipment_id, 1 + ((product_index + partner_index) % 3), qty_1, unit_price_value, line_total_value);
                    ELSIF product_index = 2 THEN
                        unit_price_value := 300 + ((partner_index + product_index) % 220);
                        line_total_value := unit_price_value * qty_2;
                        INSERT INTO shipment_items (shipment_id, product_id, quantity, unit_price, line_total)
                        VALUES (new_shipment_id, 1 + ((product_index + partner_index + 1) % 3), qty_2, unit_price_value, line_total_value);
                    ELSE
                        unit_price_value := 350 + ((partner_index + product_index) % 260);
                        line_total_value := unit_price_value * qty_3;
                        INSERT INTO shipment_items (shipment_id, product_id, quantity, unit_price, line_total)
                        VALUES (new_shipment_id, 1 + ((product_index + partner_index + 2) % 3), qty_3, unit_price_value, line_total_value);
                    END IF;
                END LOOP;

                UPDATE shipments
                SET total_amount = (
                    SELECT COALESCE(SUM(line_total), 0)
                    FROM shipment_items
                    WHERE shipment_id = new_shipment_id
                )
                WHERE shipment_id = new_shipment_id;

                remaining_quantity := remaining_quantity - current_shipment_quantity;
            END LOOP;
        END IF;
    END LOOP;
END $$;

-- Проверка итогового распределения:
-- SELECT p.partner_id, p.company_name,
--        COALESCE(SUM(si.quantity), 0) AS total_quantity
-- FROM partners p
-- LEFT JOIN shipments s ON s.partner_id = p.partner_id
-- LEFT JOIN shipment_items si ON si.shipment_id = s.shipment_id
-- GROUP BY p.partner_id, p.company_name
-- ORDER BY p.partner_id;
--
-- SELECT COUNT(*) AS zero_discount_partners
-- FROM (
--     SELECT p.partner_id
--     FROM partners p
--     LEFT JOIN shipments s ON s.partner_id = p.partner_id
--     LEFT JOIN shipment_items si ON si.shipment_id = s.shipment_id
--     GROUP BY p.partner_id
--     HAVING COALESCE(SUM(si.quantity), 0) = 0
-- ) t;
--
-- SELECT COUNT(*) AS five_percent_partners
-- FROM (
--     SELECT p.partner_id
--     FROM partners p
--     LEFT JOIN shipments s ON s.partner_id = p.partner_id
--     LEFT JOIN shipment_items si ON si.shipment_id = s.shipment_id
--     GROUP BY p.partner_id
--     HAVING COALESCE(SUM(si.quantity), 0) >= 10000 AND COALESCE(SUM(si.quantity), 0) < 50000
-- ) t;
--
-- SELECT COUNT(*) AS ten_percent_partners
-- FROM (
--     SELECT p.partner_id
--     FROM partners p
--     LEFT JOIN shipments s ON s.partner_id = p.partner_id
--     LEFT JOIN shipment_items si ON si.shipment_id = s.shipment_id
--     GROUP BY p.partner_id
--     HAVING COALESCE(SUM(si.quantity), 0) >= 50000 AND COALESCE(SUM(si.quantity), 0) < 300000
-- ) t;
--
-- SELECT COUNT(*) AS fifteen_percent_partners
-- FROM (
--     SELECT p.partner_id
--     FROM partners p
--     LEFT JOIN shipments s ON s.partner_id = p.partner_id
--     LEFT JOIN shipment_items si ON si.shipment_id = s.shipment_id
--     GROUP BY p.partner_id
--     HAVING COALESCE(SUM(si.quantity), 0) >= 300000
-- ) t;
