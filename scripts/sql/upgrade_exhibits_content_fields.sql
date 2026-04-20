ALTER TABLE exhibits
    ADD COLUMN material VARCHAR(100) NULL AFTER category,
    ADD COLUMN craft VARCHAR(100) NULL AFTER material,
    ADD COLUMN function VARCHAR(100) NULL AFTER craft,
    ADD COLUMN core_value TEXT NULL AFTER deep_intro,
    ADD COLUMN watch_points TEXT NULL AFTER core_value,
    ADD COLUMN story_points TEXT NULL AFTER watch_points,
    ADD COLUMN detail_points TEXT NULL AFTER story_points,
    ADD COLUMN kid_points TEXT NULL AFTER detail_points,
    ADD COLUMN deep_points TEXT NULL AFTER kid_points,
    ADD COLUMN keywords VARCHAR(255) NULL AFTER deep_points,
    ADD COLUMN recommended_duration_min INT NULL AFTER recommended_priority;
