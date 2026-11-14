# Login, job search and application load tests: results and bottleneck analysis

Setup: JMeter on the same MacBook as the backend (one uvicorn process, FastAPI, MySQL in Docker). Each virtual
student signs in once (login plan: signs in again and again), then repeats its request with 500 ms think time.
Every run lasted 90 s with a 30 s ramp-up (samples from the ramp-up are left out), and the backend was restarted
before every run (`loadtest/restart_backend.sh`) so one overloaded run could not spoil the next. The open-files limit
was raised to 10240 and the Mac was kept awake. Database pool: 20 + 60 connections. Error % counts HTTP errors,
dropped connections and JMeter's 60 s timeout.

## Results

| Scenario | Users | Samples | Error % | Failed logins | Avg ms | p50 ms | p95 ms | p99 ms | Max ms | Req/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Login | 100 | 1972 | 1.37 | n/a | 2500.0 | 2336 | 3310 | 4247 | 4377 | 32.57 |
| Login | 200 | 5377 | 65.45 | n/a | 1723.6 | 1999 | 4071 | 4701 | 4980 | 87.14 |
| Login | 300 | 5806 | 67.81 | n/a | 2637.6 | 3632 | 4592 | 6062 | 6694 | 92.09 |
| Login | 400 | 4912 | 80.13 | n/a | 7052.0 | 3833 | 60002 | 60003 | 60046 | 49.54 |
| Login | 500 | 525 | 100.0 | n/a | 55431.4 | 60003 | 60004 | 60009 | 60015 | 5.91 |
| Job search | 100 | 2834 | 0.78 | 0/100 | 1558.5 | 1667 | 2106 | 2338 | 2744 | 47.63 |
| Job search | 200 | 169 | 100.0 | 35/200 | 57157.1 | 60002 | 60003 | 60003 | 60003 | 1.86 |
| Job search | 300 | 193 | 100.0 | 89/300 | 54406.5 | 60003 | 60003 | 60004 | 60004 | 2.14 |
| Job search | 400 | 8524 | 76.07 | 139/400 | 2829.3 | 1206 | 3809 | 60002 | 60004 | 71.84 |
| Job search | 500 | 319 | 100.0 | 217/500 | 53231.5 | 60003 | 60004 | 60010 | 60011 | 3.52 |
| Application submission | 100 | 10854 | 0.0 | 0/100 | 35.8 | 32 | 77 | 116 | 159 | 185.58 |
| Application submission | 200 | 22347 | 0.0 | 0/200 | 22.7 | 16 | 61 | 116 | 185 | 380.56 |
| Application submission | 300 | 33585 | 0.0 | 0/300 | 21.2 | 18 | 49 | 88 | 125 | 572.28 |
| Application submission | 400 | 31744 | 0.01 | 0/400 | 235.4 | 241 | 309 | 334 | 389 | 539.08 |
| Application submission | 500 | 438 | 100.0 | 97/500 | 55207.8 | 60003 | 60003 | 60004 | 60005 | 4.84 |
| AI assistant | 5 | 5 | 40.0 | 0/5 | 125979.2 | 117700 | 180013 | 180013 | 180013 | 0.02 |
| AI assistant | 10 | 15 | 93.33 | 0/10 | 128696.4 | 120029 | 180013 | 180013 | 180013 | 0.04 |
| AI assistant | 20 | 20 | 95.0 | 0/20 | 128965.6 | 120026 | 180003 | 180003 | 180003 | 0.08 |
| AI assistant | 50 | 50 | 100.0 | 0/50 | 147991.6 | 124143 | 180003 | 180004 | 180004 | 0.21 |

Graphs: `docs/loadtest_local_crud.png` (CRUD plans) and `docs/loadtest_local_assistant.png` (assistant). Raw
numbers: `docs/loadtest_local.json`. The assistant rows are explained in `docs/loadtest_assistant_analysis.md`.

## Findings

1. **Application submission is the healthy endpoint.** 0 to 0.01 % errors from 100 to 400 users, p95 under 310 ms, and
   throughput that grows from 186 to 572 requests/s (peak at 300 users). At 400 users the median rises from 18 ms to
   241 ms, which is the sign that the server is close to full. At 500 users the run fails: only 438 samples
   finished and 97 of the 500 sign-ins failed, so the failure starts with the sign-in burst, not with the endpoint.
2. **Job search is about 12 times more expensive and collapses early.** At 100 users it works (p50 1.7 s, 47.6
   requests/s, 0.8 % errors), but the median is already 1.7 s and the server is saturated there. From 200 users on,
   the error rate is 76-100 % and most requests hit JMeter's 60 s timeout. The code explains it: `search_jobs`
   (`app/api/routes/jobs.py`) returns every matching job and `job_response` runs two extra count queries per job, so
   one search is dozens of queries on one database connection and one worker thread. With 40 worker threads the server
   cannot keep up, requests pile up, and the backend log fills with `QueuePool limit of size 20 overflow 60 reached`
   errors (HTTP 500).
3. **Login is limited by password hashing.** 100 users: p50 2.3 s, 32.6 sign-ins/s, 1.4 % errors. That is the speed
   of bcrypt on this laptop (password hashing is deliberately slow and uses a lot of CPU). From 200 users the error rate is
   65-100 %, because sign-ins arrive faster than they can be checked. The login handler also keeps its database
   connection while bcrypt runs, which makes pool exhaustion worse.
4. **Overload does not recover on its own.** An earlier run without restarts (kept in `loadtest/results/local_overload`)
   shows that after one overloaded run every later request, even at 100 users, timed out: the server keeps working
   through requests the client already abandoned, each waiting up to 30 s for a database connection, so the backlog
   never drains.
5. **The operating system limit was a bottleneck too.** With the default limit of 256 open files, the backend failed
   with `Too many open files` from 200 users on (`docs/loadtest_local_ulimit256.md`). Raising it to 10240 removed
   those errors completely.

## What would fix it (not done, so not measured)

- Job search: count applicants with one grouped query instead of two queries per job, and add a result limit
  (pagination). This should raise the 100-user capacity several times.
- Login: read the user, end the database transaction, then run bcrypt, so no connection is held during the hash; and
  run more than one backend process (several uvicorn workers or Kubernetes replicas), because bcrypt is CPU bound.
- Overload protection: a bounded request queue (answer quickly with 503 when full) so abandoned requests do not pile up.
- The same tests against AWS will show how much of this is the single laptop (one CPU, MySQL and JMeter on the
  same machine) and how much is the application.
