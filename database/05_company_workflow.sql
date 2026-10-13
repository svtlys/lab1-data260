-- Week 3 migration: ownership, deadlines, eligibility, applications.
-- Run ONCE, after 02_schema.sql:   mysql -u root -P 3307 p16_handshake < database/05_company_workflow.sql
-- (MySQL has no "ADD COLUMN IF NOT EXISTS"; a second run fails with "Duplicate column".
--  To redo it, drop and recreate the database and run 02 then 05 again.)

-- Jobs: who posted it, and when applications close.
ALTER TABLE jobs
  ADD COLUMN company_id INT NULL AFTER id,
  ADD COLUMN deadline DATE NULL,
  ADD CONSTRAINT fk_jobs_company FOREIGN KEY (company_id) REFERENCES company_profiles(id) ON DELETE CASCADE,
  ADD INDEX idx_jobs_company (company_id),
  ADD INDEX idx_jobs_city (city);

-- Events: who created it and who may attend.
--   eligible_majors  comma-separated list, NULL = every major
--   min_cgpa         NULL = no GPA requirement
--   min_grad_year / max_grad_year  NULL = no limit
ALTER TABLE events
  ADD COLUMN company_id INT NULL AFTER id,
  ADD COLUMN eligible_majors VARCHAR(500) NULL,
  ADD COLUMN min_cgpa DECIMAL(3,2) NULL,
  ADD COLUMN min_grad_year INT NULL,
  ADD COLUMN max_grad_year INT NULL,
  ADD COLUMN eligibility_note VARCHAR(500) NULL,
  ADD CONSTRAINT fk_events_company FOREIGN KEY (company_id) REFERENCES company_profiles(id) ON DELETE CASCADE,
  ADD INDEX idx_events_company (company_id),
  ADD INDEX idx_events_date (event_date);

-- Applications (the Week 2 student workflow needs this table too).
CREATE TABLE IF NOT EXISTS applications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  job_id INT NOT NULL,
  student_id INT NOT NULL,
  status ENUM('Pending','Reviewed','Declined') NOT NULL DEFAULT 'Pending',
  applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  resume_filename VARCHAR(255) NULL,
  resume_path VARCHAR(500) NULL,
  CONSTRAINT fk_app_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
  CONSTRAINT fk_app_student FOREIGN KEY (student_id) REFERENCES student_profiles(id) ON DELETE CASCADE,
  CONSTRAINT uq_app_job_student UNIQUE (job_id, student_id),
  INDEX idx_app_student (student_id),
  INDEX idx_app_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
