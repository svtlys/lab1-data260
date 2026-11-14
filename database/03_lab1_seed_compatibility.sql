-- align the lab 1 schema with the current application models.

USE p16_handshake;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'jobs'
              AND column_name = 'company_id'
        ),
        'SELECT 1',
        'ALTER TABLE jobs ADD COLUMN company_id INT NULL AFTER id'
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
              AND table_name = 'jobs'
              AND column_name = 'deadline'
        ),
        'SELECT 1',
        'ALTER TABLE jobs ADD COLUMN deadline DATE NULL AFTER posted_at'
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
              AND table_name = 'jobs'
              AND index_name = 'idx_jobs_company_id'
        ),
        'SELECT 1',
        'ALTER TABLE jobs ADD INDEX idx_jobs_company_id (company_id)'
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
              AND table_name = 'jobs'
              AND column_name = 'company_id'
              AND referenced_table_name = 'company_profiles'
              AND referenced_column_name = 'id'
        ),
        'SELECT 1',
        'ALTER TABLE jobs ADD CONSTRAINT fk_jobs_company_profile FOREIGN KEY (company_id) REFERENCES company_profiles(id) ON DELETE CASCADE'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

CREATE TABLE IF NOT EXISTS applications (
    id INT NOT NULL AUTO_INCREMENT,
    job_id INT NOT NULL,
    student_id INT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Pending',
    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resume_filename VARCHAR(255) NULL,
    resume_path VARCHAR(500) NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_app_job_student (job_id, student_id),
    KEY idx_applications_job_id (job_id),
    KEY idx_applications_student_id (student_id),
    CONSTRAINT fk_application_job FOREIGN KEY (job_id)
        REFERENCES jobs (id) ON DELETE CASCADE,
    CONSTRAINT fk_application_student FOREIGN KEY (student_id)
        REFERENCES student_profiles (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
