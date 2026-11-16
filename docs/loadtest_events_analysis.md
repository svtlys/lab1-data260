# Event search and event registration load tests (local laptop)

JMeter plans `event_search.jmx` and `event_register.jmx`, 100 to 500 users, 90 s per run with a 30 s ramp-up
(left out of the numbers), 500 ms think time, backend restarted before every run (`RESTART_CMD=./restart_backend.sh`),
open-files limit 10240. Each student signs in once and then repeats its request. Raw numbers: `docs/loadtest_local_events.json`,
table: `docs/loadtest_local_events.md`, graph: `docs/loadtest_local_events_crud.png`.

| Scenario | Users | Samples | Error % | Failed logins | Avg ms | p50 ms | p95 ms | p99 ms | Max ms | Req/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Event search | 100 | 11316 | 0.0 | 0/100 | 14.5 | 12 | 31 | 61 | 106 | 192.93 |
| Event search | 200 | 22643 | 0.0 | 0/200 | 16.2 | 11 | 49 | 108 | 210 | 385.8 |
| Event search | 300 | 34266 | 0.0 | 0/300 | 11.3 | 9 | 21 | 75 | 135 | 585.14 |
| Event search | 400 | 45078 | 0.0 | 0/400 | 16.1 | 12 | 51 | 80 | 137 | 768.24 |
| Event search | 500 | 356 | 100.0 | 178/500 | 54271.9 | 60002 | 60003 | 60003 | 60004 | 3.93 |
| Event registration | 100 | 10935 | 0.05 | 0/100 | 31.1 | 27 | 67 | 99 | 187 | 186.53 |
| Event registration | 200 | 22082 | 0.07 | 0/200 | 28.2 | 18 | 87 | 122 | 178 | 376.5 |
| Event registration | 300 | 34078 | 0.0 | 0/300 | 14.5 | 12 | 30 | 75 | 132 | 580.86 |
| Event registration | 400 | 43090 | 1.02 | 2/400 | 39.2 | 23 | 116 | 199 | 643 | 733.95 |
| Event registration | 500 | 401 | 100.0 | 134/500 | 54764.8 | 60002 | 60005 | 60006 | 60008 | 4.43 |

## What the runs show

**Event search is fast and scales to 400 users.** Every run from 100 to 400 users finished with zero errors. The 95th percentile stayed
between 21 and 51 ms and throughput grew almost linearly with users (193, 386, 585, 768 requests/s). The endpoint is one SQL query with a
`LIKE` filter over 100 event rows, so there is little work per request. For comparison, job search (`docs/loadtest_crud_analysis.md`) runs
two extra queries for every matching job and already failed at 200 users.

**Both plans break at 500 users, and the break is not about the endpoints.** At 500 users 100 % of the steady-state samples failed, 178 and 134
of the 500 sign-ins failed, and the median response time was 60 s, which is JMeter's response timeout. JMeter received no HTTP response at all
(`SocketTimeoutException` and `NoHttpResponseException` only), so the server stopped answering instead of returning errors. This is the same
failure as the other plans at 500 users: the burst of sign-ins at the start of the run (bcrypt is slow on purpose, and every request needs a
database connection for authentication) fills the backend and it does not recover.

**Registration at 400 users is the first sign of the limit.** Error rate rose to 1.02 %: 184 responses were HTTP 500 and 253 were dropped
connections. The backend log for that run holds `QueuePool limit of size 20 overflow 60 reached, connection timed out` tracebacks raised in
`get_current_user`, the authentication dependency that every protected request goes through. So the database connection pool (20 + 60
connections) is what runs out first. Registration needs more connection time per request than search, which is why search still passed at
400 users. The 100- and 200-user registration runs had 3 and 8 HTTP 500 responses (0.05 % and 0.07 %), probably the same cause at a smaller scale.

## How to read the registration numbers

Registrations are saved to the database and are not reset between runs, and each student can register for an event only once. Most
responses were therefore 409 (already registered, or the event is full) or 403 (the student is not eligible for that event): at 100 users
324 requests created a registration (201), at 200 users 75, at 300 users 35 and at 400 users 15. These are correct answers from the
service, so they count as successes. It also means the registration plan mostly measures the lookup and eligibility path, not the insert.
A run that measures inserts needs a freshly seeded database.

## Limits of these results

- One laptop runs the backend, MySQL, JMeter and the browser; the numbers show the shape of the limits, not production capacity.
- A single run per level; the 400-user registration result (1 % errors) sits close to the failure point and could differ on a rerun.
- The 500-user cause is inferred from the logs of this and the earlier CRUD runs (pool timeouts, bcrypt sign-in burst); it was not isolated
  by an experiment such as raising the pool size again.
