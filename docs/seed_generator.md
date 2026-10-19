# Seed generator safety guide

The repeatable Pair 16 seed generator is located at
`backend/scripts/generate_seed_data.py`.

It produces:

- 50 companies and 50 company users.
- 200 students and 200 student users.
- 300 jobs.
- 1,500 applications with unique job/student pairs.
- 100 events.
- Eligible event registrations without duplicate event/student pairs or capacity violations.

The generator uses seed `16`, a fixed anchor date, and only these cities:
Sunnyvale, Cupertino, and Mountain View.

## safe preview commands

Run these from the `backend` folder with the existing virtual environment active:

```powershell
.\.venv\Scripts\python.exe scripts\generate_seed_data.py --summary
.\.venv\Scripts\python.exe scripts\generate_seed_data.py --dry-run
```

Both commands generate and validate data in memory. They do not connect to MySQL
and do not change database records.

## SQL output

This command writes insert-only SQL and does not connect to MySQL:

```powershell
.\.venv\Scripts\python.exe scripts\generate_seed_data.py --sql-out seed_preview.sql
```

The generated SQL may conflict with existing IDs or unique values, so review it
before any use. The optional `--include-delete` flag adds destructive `DELETE`
statements and must not be used against a database containing real data.

## reset behavior

`--reset` clears existing users, profiles, jobs, applications, events,
registrations, saved items, and assistant records before loading generated data.
It requires the explicit `--confirm-reset` flag and is intended only for an
isolated development database. Do not run it against shared or real user data.

## tests

From the `backend` folder:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_seed_generator
```

The tests run entirely in memory and verify the seed, required counts, city
restrictions, deterministic output, duplicate prevention, and insert-only SQL.
