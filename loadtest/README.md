# Load tests (Lab 2, Part 5)

JMeter plans for Pair 16. Install JMeter once: `brew install jmeter` (needs Java).

1. `python make_plans.py` (run once after cloning: it creates `students.csv`, which is not committed because it holds the demo password; the `.jmx` plans are committed)
2. Start the backend (and MySQL). The seeded students (student1..200) must exist.
3. Smoke test, 1 user per plan, about 2 minutes: `./run_tests.sh smoke`
4. Real runs: `./run_tests.sh local` (or `./run_tests.sh aws <elb-hostname> 80`)
5. Numbers and graphs: `python summarize.py local`

Plans: `login.jmx`, `job_search.jmx`, `apply.jmx` (100 to 500 users) and `assistant.jmx` (5, 10, 20, 50 users).
See the comments in `run_tests.sh` for the options (shorter runs, only some plans, JMeter HTML report).
