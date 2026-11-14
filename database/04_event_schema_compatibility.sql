-- align the event table with the current event model.

USE p16_handshake;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'events'
              AND column_name = 'company_id'
        ),
        'SELECT 1',
        'ALTER TABLE events ADD COLUMN company_id INT NULL AFTER id'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'events'
              AND column_name = 'eligible_majors'
        ),
        'SELECT 1',
        'ALTER TABLE events ADD COLUMN eligible_majors VARCHAR(500) NULL AFTER capacity'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'events'
              AND column_name = 'min_cgpa'
        ),
        'SELECT 1',
        'ALTER TABLE events ADD COLUMN min_cgpa DECIMAL(3,2) NULL AFTER eligible_majors'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'events'
              AND column_name = 'min_grad_year'
        ),
        'SELECT 1',
        'ALTER TABLE events ADD COLUMN min_grad_year INT NULL AFTER min_cgpa'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'events'
              AND column_name = 'max_grad_year'
        ),
        'SELECT 1',
        'ALTER TABLE events ADD COLUMN max_grad_year INT NULL AFTER min_grad_year'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'events'
              AND column_name = 'eligibility_note'
        ),
        'SELECT 1',
        'ALTER TABLE events ADD COLUMN eligibility_note VARCHAR(500) NULL AFTER max_grad_year'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1
            FROM information_schema.statistics
            WHERE table_schema = DATABASE()
              AND table_name = 'events'
              AND index_name = 'idx_events_company_id'
        ),
        'SELECT 1',
        'ALTER TABLE events ADD INDEX idx_events_company_id (company_id)'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1
            FROM information_schema.key_column_usage
            WHERE table_schema = DATABASE()
              AND table_name = 'events'
              AND column_name = 'company_id'
              AND referenced_table_name = 'company_profiles'
              AND referenced_column_name = 'id'
        ),
        'SELECT 1',
        'ALTER TABLE events ADD CONSTRAINT fk_events_company_profile FOREIGN KEY (company_id) REFERENCES company_profiles(id) ON DELETE CASCADE'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
