// Shared constants so category / status values live in exactly one place.
// If the backend stores different values (e.g. "full_time"), change them here
// and every form, filter, and badge follows.

// Must match jobs.employment_type in the database (and the seed generator).
export const JOB_CATEGORIES = ['Full-time', 'Part-time', 'On-campus', 'Internship']

export const APPLICATION_STATUSES = ['Pending', 'Reviewed', 'Declined']

// Pair 16 CITY_SET (from docs/backend.md). Used only as location suggestions.
export const CITY_SET = ['Sunnyvale', 'Cupertino', 'Mountain View']

// Must match events.event_type (and the seed generator).
export const EVENT_TYPES = ['Career Fair', 'Workshop', 'Info Session', 'Networking', 'Hackathon', 'Panel']

// Majors offered as eligibility choices and used by the seed data.
export const MAJORS = [
  'Computer Science',
  'Data Analytics',
  'Software Engineering',
  'Electrical Engineering',
  'Business Analytics',
  'Information Systems',
  'Mathematics',
  'Statistics',
]
