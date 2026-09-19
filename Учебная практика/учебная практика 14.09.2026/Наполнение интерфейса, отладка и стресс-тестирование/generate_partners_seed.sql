-- =====================================================
-- Генерация данных для наполнения partners до 100 записей
-- и формирования истории продаж от 0 до 5 отгрузок на партнера
--
-- ВАЖНО:
-- Этот тестовый скрипт
-- =====================================================

-- Базовая структура данных в таблице partners:
-- partner_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY
-- company_name    VARCHAR(255) NOT NULL
-- inn             VARCHAR(12) NOT NULL UNIQUE
-- contact_email   VARCHAR(255) NOT NULL UNIQUE
-- phone           VARCHAR(20) NOT NULL
-- rating          DECIMAL(3,2) NOT NULL
--
-- В базе уже есть реальные данные:
-- 1, 'ООО "Логистик-Экспресс"', '...','info@logex.ru','+79991112233', 4.80
-- 2, 'ИП Петров А.В.', '...','petrov_delivery@mail.ru','+79041112233', 4.50
-- 3, 'ТК "Быстрый Путь"', '...','speedway@yandex.ru','+78125554433', 4.20
--
-- Поэтому формат телефонных номеров сохраняется в виде:
-- +7XXXXXXXXXX
-- без пробелов, скобок и тире.

DO $$
DECLARE
    target_count INTEGER := 100;
    current_count INTEGER;
    needed_count INTEGER;
    partner_index INTEGER;
    shipment_count INTEGER;
    shipment_index INTEGER;
    product_index INTEGER;
    quantity_value INTEGER;
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
    max_partner_id INTEGER;
    max_shipment_id INTEGER;
    max_shipment_item_id INTEGER;
    max_product_id INTEGER;
BEGIN
    -- Синхронизируем identity sequence для всех таблиц, чтобы повторный запуск
    -- не падал на duplicate key по partner_id / shipment_id / shipment_item_id.
    SELECT COALESCE(MAX(partner_id), 0) INTO max_partner_id FROM partners;
    PERFORM setval(pg_get_serial_sequence('partners', 'partner_id'), max_partner_id, true);

    SELECT COALESCE(MAX(shipment_id), 0) INTO max_shipment_id FROM shipments;
    PERFORM setval(pg_get_serial_sequence('shipments', 'shipment_id'), max_shipment_id, true);

    SELECT COALESCE(MAX(shipment_item_id), 0) INTO max_shipment_item_id FROM shipment_items;
    PERFORM setval(pg_get_serial_sequence('shipment_items', 'shipment_item_id'), max_shipment_item_id, true);

    SELECT COALESCE(MAX(product_id), 0) INTO max_product_id FROM products;
    PERFORM setval(pg_get_serial_sequence('products', 'product_id'), max_product_id, true);

    SELECT COUNT(*) INTO current_count FROM partners;
    needed_count := target_count - current_count;

    -- Если нужно меньше нуля — ничего не делаем.
    IF needed_count <= 0 THEN
        RETURN;
    END IF;

    -- 1) Добавляем недостающих партнеров.
    FOR partner_index IN 1..needed_count LOOP
        company_name_text := 'ООО "Партнер ' || (current_count + partner_index) || '"';
        inn_text := LPAD(CAST((900000000 + current_count + partner_index) AS TEXT), 10, '0');
        email_text := 'partner' || (current_count + partner_index) || '@example.ru';

        CASE (current_count + partner_index) % 8
            WHEN 0 THEN phone_text := '+7495' || LPAD(CAST((1000000 + current_count + partner_index) AS TEXT), 7, '0');
            WHEN 1 THEN phone_text := '+7812' || LPAD(CAST((1000000 + current_count + partner_index) AS TEXT), 7, '0');
            WHEN 2 THEN phone_text := '+7900' || LPAD(CAST((1000000 + current_count + partner_index) AS TEXT), 7, '0');
            WHEN 3 THEN phone_text := '+7904' || LPAD(CAST((1000000 + current_count + partner_index) AS TEXT), 7, '0');
            WHEN 4 THEN phone_text := '+7911' || LPAD(CAST((1000000 + current_count + partner_index) AS TEXT), 7, '0');
            WHEN 5 THEN phone_text := '+7921' || LPAD(CAST((1000000 + current_count + partner_index) AS TEXT), 7, '0');
            WHEN 6 THEN phone_text := '+7499' || LPAD(CAST((1000000 + current_count + partner_index) AS TEXT), 7, '0');
            ELSE phone_text := '+7909' || LPAD(CAST((1000000 + current_count + partner_index) AS TEXT), 7, '0');
        END CASE;

        rating_value := ROUND((0.50 + ((current_count + partner_index) % 5) * 0.80 + ((current_count + partner_index) % 3) * 0.15), 2);

        INSERT INTO partners (company_name, inn, contact_email, phone, rating)
        VALUES (
            company_name_text,
            inn_text,
            email_text,
            phone_text,
            rating_value
        )
        ON CONFLICT (contact_email) DO NOTHING;

        -- На этом этапе запись партнера создана.
        SELECT partner_id INTO new_partner_id
        FROM partners
        WHERE contact_email = email_text;

        -- 2) Для каждого партнера добавляем от 0 до 5 отгрузок.
        -- Это нужно, чтобы проверить:
        -- - партнер без продаж -> 0%
        -- - партнер с историей -> рассчитанная скидка
        -- - приложение не падает при SUM(quantity) IS NULL
        shipment_count := (current_count + partner_index) % 6; -- 0..5

        FOR shipment_index IN 1..shipment_count LOOP
            shipment_date_value := DATE '2026-01-01' + ((current_count + partner_index) * 3 + shipment_index * 7) % 180;

            INSERT INTO shipments (partner_id, shipment_date, total_amount)
            VALUES (
                new_partner_id,
                shipment_date_value,
                0
            )
            RETURNING shipment_id INTO new_shipment_id;

            -- Создаем 1..3 строки товаров в отгрузке.
            FOR product_index IN 1..(1 + ((current_count + partner_index + shipment_index) % 3)) LOOP
                quantity_value := 5 + ((current_count + partner_index + shipment_index + product_index) % 25);
                unit_price_value := (50 + product_index * 25) + ((current_count + partner_index) % 15);
                line_total_value := unit_price_value * quantity_value;

                INSERT INTO shipment_items (shipment_id, product_id, quantity, unit_price, line_total)
                VALUES (
                    new_shipment_id,
                    1 + ((product_index + ((current_count + partner_index + shipment_index) % 3)) % max_product_id),
                    quantity_value,
                    unit_price_value,
                    line_total_value
                );
            END LOOP;

            UPDATE shipments
            SET total_amount = (
                SELECT COALESCE(SUM(line_total), 0)
                FROM shipment_items
                WHERE shipment_id = new_shipment_id
            )
            WHERE shipment_id = new_shipment_id;
        END LOOP;
    END LOOP;
END $$;

-- =====================================================
-- После запуска можно проверить:
-- 1) общее количество партнеров
-- SELECT COUNT(*) AS total_partners FROM partners;
--
-- 2) партнеры без продаж
-- SELECT p.partner_id, p.company_name, COUNT(s.shipment_id) AS shipment_count
-- FROM partners p
-- LEFT JOIN shipments s ON s.partner_id = p.partner_id
-- GROUP BY p.partner_id, p.company_name
-- HAVING COUNT(s.shipment_id) = 0
-- ORDER BY p.partner_id;
--
-- 3) проверка, что у некоторых партнеров будет 0% и приложение не упадет
-- SELECT p.partner_id, p.company_name,
--        COALESCE(SUM(si.quantity), 0) AS total_quantity,
--        CASE
--            WHEN COALESCE(SUM(si.quantity), 0) IS NULL THEN 0
--            WHEN COALESCE(SUM(si.quantity), 0) = 0 THEN 0
--            ELSE 0
--        END AS discount_percent
-- FROM partners p
-- LEFT JOIN shipments s ON s.partner_id = p.partner_id
-- LEFT JOIN shipment_items si ON si.shipment_id = s.shipment_id
-- GROUP BY p.partner_id, p.company_name
-- ORDER BY p.partner_id;
--
-- 4) общая сводка по истории продаж
-- SELECT p.partner_id, p.company_name, COUNT(s.shipment_id) AS shipment_count,
--        COALESCE(SUM(si.quantity), 0) AS total_quantity
-- FROM partners p
-- LEFT JOIN shipments s ON s.partner_id = p.partner_id
-- LEFT JOIN shipment_items si ON si.shipment_id = s.shipment_id
-- GROUP BY p.partner_id, p.company_name
-- ORDER BY p.partner_id;
-- =====================================================
