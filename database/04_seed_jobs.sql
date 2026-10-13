-- use the pair 16 database
USE p16_handshake;

-- add a sunnyvale software internship when it is not already present
INSERT INTO jobs (
    title, description, company_name, location, city, employment_type,
    is_remote, salary_min, salary_max, required_skills, posted_at
)
SELECT
    'Software Engineering Intern',
    'Build backend features with a small product engineering team.',
    'Sunnyvale Cloud Labs',
    'Sunnyvale office',
    'Sunnyvale',
    'internship',
    FALSE,
    28.00,
    35.00,
    'Python, FastAPI, SQL',
    '2026-10-01 09:00:00'
FROM (SELECT 1) AS seed
WHERE NOT EXISTS (SELECT 1 FROM jobs WHERE title = 'Software Engineering Intern');

-- add a sunnyvale data analyst role when it is not already present
INSERT INTO jobs (
    title, description, company_name, location, city, employment_type,
    is_remote, salary_min, salary_max, required_skills, posted_at
)
SELECT
    'Junior Data Analyst',
    'Turn product data into dashboards and clear business recommendations.',
    'Sunnyvale Insights',
    'Sunnyvale office',
    'Sunnyvale',
    'full-time',
    FALSE,
    72000.00,
    85000.00,
    'SQL, Excel, data visualization',
    '2026-10-03 09:00:00'
FROM (SELECT 1) AS seed
WHERE NOT EXISTS (SELECT 1 FROM jobs WHERE title = 'Junior Data Analyst');

-- add a cupertino frontend role when it is not already present
INSERT INTO jobs (
    title, description, company_name, location, city, employment_type,
    is_remote, salary_min, salary_max, required_skills, posted_at
)
SELECT
    'Frontend Developer Intern',
    'Create accessible React interfaces for student-facing products.',
    'Cupertino Learning Systems',
    'Cupertino office',
    'Cupertino',
    'internship',
    FALSE,
    26.00,
    32.00,
    'React, JavaScript, CSS',
    '2026-10-05 09:00:00'
FROM (SELECT 1) AS seed
WHERE NOT EXISTS (SELECT 1 FROM jobs WHERE title = 'Frontend Developer Intern');

-- add a cupertino remote role when it is not already present
INSERT INTO jobs (
    title, description, company_name, location, city, employment_type,
    is_remote, salary_min, salary_max, required_skills, posted_at
)
SELECT
    'Product Operations Associate',
    'Coordinate product feedback and improve team operating processes.',
    'Cupertino Product Works',
    'Online',
    'Cupertino',
    'full-time',
    TRUE,
    68000.00,
    78000.00,
    'communication, research, project management',
    '2026-10-06 09:00:00'
FROM (SELECT 1) AS seed
WHERE NOT EXISTS (SELECT 1 FROM jobs WHERE title = 'Product Operations Associate');

-- add a mountain view machine learning role when it is not already present
INSERT INTO jobs (
    title, description, company_name, location, city, employment_type,
    is_remote, salary_min, salary_max, required_skills, posted_at
)
SELECT
    'Machine Learning Research Assistant',
    'Support experiments involving language models and evaluation datasets.',
    'Mountain View AI Studio',
    'Mountain View lab',
    'Mountain View',
    'part-time',
    FALSE,
    30.00,
    38.00,
    'Python, statistics, machine learning',
    '2026-10-08 09:00:00'
FROM (SELECT 1) AS seed
WHERE NOT EXISTS (SELECT 1 FROM jobs WHERE title = 'Machine Learning Research Assistant');

-- add a mountain view cybersecurity role when it is not already present
INSERT INTO jobs (
    title, description, company_name, location, city, employment_type,
    is_remote, salary_min, salary_max, required_skills, posted_at
)
SELECT
    'Cybersecurity Analyst Intern',
    'Help monitor security alerts and document practical security controls.',
    'Mountain View Secure',
    'Mountain View office',
    'Mountain View',
    'internship',
    FALSE,
    27.00,
    34.00,
    'Linux, networking, security fundamentals',
    '2026-10-09 09:00:00'
FROM (SELECT 1) AS seed
WHERE NOT EXISTS (SELECT 1 FROM jobs WHERE title = 'Cybersecurity Analyst Intern');

-- confirm the seeded jobs by city
SELECT city, COUNT(*) AS job_count
FROM jobs
GROUP BY city
ORDER BY city;
