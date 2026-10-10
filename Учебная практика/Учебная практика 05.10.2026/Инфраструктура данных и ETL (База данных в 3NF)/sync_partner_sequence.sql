-- Выполнять под блокировкой partners после загрузки явных CSV ID.
-- Не возвращаем последовательность назад даже после удаления строк вручную.
SELECT setval(
    'practice_2026_10_05.partners_partner_id_seq',
    GREATEST(
        COALESCE((SELECT max(partner_id)::BIGINT FROM practice_2026_10_05.partners), 0) + 1,
        (SELECT last_value + CASE WHEN is_called THEN 1 ELSE 0 END
         FROM practice_2026_10_05.partners_partner_id_seq)
    ),
    false
);
