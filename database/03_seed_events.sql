-- use the pair 16 database
USE p16_handshake;

-- add a sunnyvale technology event when it is not already present
INSERT INTO events (
    title,
    description,
    organizer,
    location,
    city,
    event_date,
    event_type,
    is_virtual,
    capacity
)
SELECT
    'Sunnyvale Technology Career Fair',
    'Meet technology employers and learn about student internship opportunities.',
    'Pair 16 Career Network',
    'Sunnyvale Civic Center',
    'Sunnyvale',
    '2026-10-17 10:00:00',
    'career fair',
    FALSE,
    250
FROM (SELECT 1) AS seed
WHERE NOT EXISTS (
    SELECT 1 FROM events
    WHERE title = 'Sunnyvale Technology Career Fair'
);

-- add a sunnyvale resume workshop when it is not already present
INSERT INTO events (
    title,
    description,
    organizer,
    location,
    city,
    event_date,
    event_type,
    is_virtual,
    capacity
)
SELECT
    'Resume Workshop for Students',
    'Practice writing clear resumes and preparing for technical interviews.',
    'Sunnyvale Student Success Center',
    'Online',
    'Sunnyvale',
    '2026-10-20 18:00:00',
    'workshop',
    TRUE,
    100
FROM (SELECT 1) AS seed
WHERE NOT EXISTS (
    SELECT 1 FROM events
    WHERE title = 'Resume Workshop for Students'
);

-- add a cupertino networking event when it is not already present
INSERT INTO events (
    title,
    description,
    organizer,
    location,
    city,
    event_date,
    event_type,
    is_virtual,
    capacity
)
SELECT
    'Cupertino Startup Networking Night',
    'Connect with founders, mentors, and students interested in startups.',
    'Cupertino Innovation Hub',
    'Cupertino Community Hall',
    'Cupertino',
    '2026-10-24 17:30:00',
    'networking',
    FALSE,
    150
FROM (SELECT 1) AS seed
WHERE NOT EXISTS (
    SELECT 1 FROM events
    WHERE title = 'Cupertino Startup Networking Night'
);

-- add a cupertino data event when it is not already present
INSERT INTO events (
    title,
    description,
    organizer,
    location,
    city,
    event_date,
    event_type,
    is_virtual,
    capacity
)
SELECT
    'Data Careers Panel',
    'Hear data professionals discuss analytics, engineering, and career paths.',
    'DATA 260 Alumni Group',
    'Online',
    'Cupertino',
    '2026-10-28 19:00:00',
    'panel',
    TRUE,
    200
FROM (SELECT 1) AS seed
WHERE NOT EXISTS (
    SELECT 1 FROM events
    WHERE title = 'Data Careers Panel'
);

-- add a mountain view engineering event when it is not already present
INSERT INTO events (
    title,
    description,
    organizer,
    location,
    city,
    event_date,
    event_type,
    is_virtual,
    capacity
)
SELECT
    'Mountain View Engineering Meetup',
    'Explore software engineering projects and meet local engineering teams.',
    'Mountain View Engineering Society',
    'Mountain View Library',
    'Mountain View',
    '2026-11-05 18:30:00',
    'meetup',
    FALSE,
    120
FROM (SELECT 1) AS seed
WHERE NOT EXISTS (
    SELECT 1 FROM events
    WHERE title = 'Mountain View Engineering Meetup'
);

-- add a mountain view mock interview event when it is not already present
INSERT INTO events (
    title,
    description,
    organizer,
    location,
    city,
    event_date,
    event_type,
    is_virtual,
    capacity
)
SELECT
    'Mock Interview Practice Day',
    'Complete practice interviews and receive feedback from volunteer mentors.',
    'Mountain View Career Mentors',
    'Mountain View Community Center',
    'Mountain View',
    '2026-11-12 09:00:00',
    'career preparation',
    FALSE,
    60
FROM (SELECT 1) AS seed
WHERE NOT EXISTS (
    SELECT 1 FROM events
    WHERE title = 'Mock Interview Practice Day'
);

-- confirm the seeded events by city
SELECT city, COUNT(*) AS event_count
FROM events
GROUP BY city
ORDER BY city;
