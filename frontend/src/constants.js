// Shared constants so category / status values live in exactly one place.
// If the backend stores different values (e.g. "full_time"), change them here
// and every form, filter, and badge follows.

export const JOB_CATEGORIES = ['Full-time', 'Part-time', 'On-campus', 'Internship']

export const APPLICATION_STATUSES = ['Pending', 'Reviewed', 'Declined']

// Pair 16 CITY_SET (from docs/backend.md). Used only as location suggestions.
export const CITY_SET = ['Sunnyvale', 'Cupertino', 'Mountain View']
