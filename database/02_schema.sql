-- use the pair 16 database
USE p16_handshake;

-- store login and authorization information
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    role ENUM('student', 'company') NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);

-- store information that belongs specifically to students
CREATE TABLE IF NOT EXISTS student_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    college_name VARCHAR(200) NOT NULL,
    career_objective TEXT,
    date_of_birth DATE,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    degree VARCHAR(150),
    major VARCHAR(150),
    graduation_year SMALLINT,
    cgpa DECIMAL(4,2),
    experience TEXT,
    skills TEXT,
    phone VARCHAR(30),
    profile_picture_url VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_student_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);

-- store information that belongs specifically to companies
CREATE TABLE IF NOT EXISTS company_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    company_name VARCHAR(200) NOT NULL,
    location VARCHAR(200) NOT NULL,
    description TEXT,
    contact_phone VARCHAR(30),
    profile_picture_url VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_company_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);

-- store events that students can discover and attend
CREATE TABLE IF NOT EXISTS events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    organizer VARCHAR(200) NOT NULL,
    location VARCHAR(200) NOT NULL,
    city VARCHAR(100) NOT NULL,
    event_date DATETIME NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    is_virtual BOOLEAN NOT NULL DEFAULT FALSE,
    capacity INT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);

-- connect students to the events they registered for
CREATE TABLE IF NOT EXISTS event_registrations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    student_id INT NOT NULL,
    registered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_event_student UNIQUE (event_id, student_id),
    CONSTRAINT fk_registration_event
        FOREIGN KEY (event_id) REFERENCES events(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_registration_student
        FOREIGN KEY (student_id) REFERENCES student_profiles(id)
        ON DELETE CASCADE
);

-- store job opportunities that students can search
CREATE TABLE IF NOT EXISTS jobs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    company_name VARCHAR(200) NOT NULL,
    location VARCHAR(200) NOT NULL,
    city VARCHAR(100) NOT NULL,
    employment_type VARCHAR(100) NOT NULL,
    is_remote BOOLEAN NOT NULL DEFAULT FALSE,
    salary_min DECIMAL(12,2) NULL,
    salary_max DECIMAL(12,2) NULL,
    required_skills TEXT,
    posted_at DATETIME NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);

-- store jobs or events saved by students for later review
CREATE TABLE IF NOT EXISTS saved_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    job_id INT NULL,
    event_id INT NULL,
    saved_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_saved_student_job UNIQUE (student_id, job_id),
    CONSTRAINT uq_saved_student_event UNIQUE (student_id, event_id),
    CONSTRAINT chk_saved_item_type CHECK (
        (job_id IS NOT NULL AND event_id IS NULL)
        OR (job_id IS NULL AND event_id IS NOT NULL)
    ),
    CONSTRAINT fk_saved_item_student
        FOREIGN KEY (student_id) REFERENCES student_profiles(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_saved_item_job
        FOREIGN KEY (job_id) REFERENCES jobs(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_saved_item_event
        FOREIGN KEY (event_id) REFERENCES events(id)
        ON DELETE CASCADE
);

-- store one assistant conversation for each student session
CREATE TABLE IF NOT EXISTS assistant_conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_conversation_student
        FOREIGN KEY (student_id) REFERENCES student_profiles(id)
        ON DELETE CASCADE
);

-- store the ordered messages that make up a conversation history
CREATE TABLE IF NOT EXISTS assistant_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL,
    role VARCHAR(30) NOT NULL,
    content TEXT NOT NULL,
    sequence_number INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_conversation_sequence
        UNIQUE (conversation_id, sequence_number),
    CONSTRAINT fk_message_conversation
        FOREIGN KEY (conversation_id) REFERENCES assistant_conversations(id)
        ON DELETE CASCADE
);

-- store every manual tool call for debugging and grading evidence
CREATE TABLE IF NOT EXISTS assistant_tool_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL,
    iteration INT NOT NULL,
    tool_call_id VARCHAR(150) NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    arguments_json JSON NOT NULL,
    result_json JSON NULL,
    error_message TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tool_log_conversation
        FOREIGN KEY (conversation_id) REFERENCES assistant_conversations(id)
        ON DELETE CASCADE
);

-- confirm that all current tables were created
SHOW TABLES;
