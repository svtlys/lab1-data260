#!/usr/bin/env python3
"""Seed-data generator for the Handshake lab (Pair 16).

Produces, deterministically (random.Random(SEED), fixed anchor date):
    50 companies (+50 company users), 200 students (+200 student users),
    300 jobs, 1,500 applications, 100 events, ~event registrations.
Every foreign key is valid by construction, and registrations respect each
event's eligibility rules and capacity (same rule the app uses).

Usage (from the backend/ folder, with the venv active):

    python scripts/generate_seed_data.py --reset            # write into MySQL (reads backend/.env)
    python scripts/generate_seed_data.py --sql-out seed.sql  # just write a .sql file, no DB needed
    python scripts/generate_seed_data.py --summary           # print counts, touch nothing

--reset EMPTIES these tables first (users, student_profiles, company_profiles,
jobs, events, event_registrations, applications, saved_items and the assistant_*
tables) -- including any hand-made rows from the older seed file. Run it
only on your development database.

All seeded accounts share one password (SEED_PASSWORD below) so you can log in as
any of them while testing: student1@students.handshake-demo.com / Password123!
"""
import argparse
import os
import random
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------- lab config
SEED = 16
CITY_SET = ["Sunnyvale", "Cupertino", "Mountain View"]
N_COMPANIES, N_STUDENTS, N_JOBS, N_APPLICATIONS, N_EVENTS = 50, 200, 300, 1500, 100
ANCHOR = datetime(2026, 10, 12, 9, 0, 0)  # fixed "today" so output never depends on the run date

SEED_PASSWORD = "Password123!"
# bcrypt ($2b$, cost 12) of SEED_PASSWORD, computed once. Hashing 250 passwords at
# runtime would take ~1 minute; one shared hash is fine for demo data.
SEED_PASSWORD_HASH = "$2b$12$OSw0q3cl88tistvSXCTSB.nddSHA5h8dksVqUEeg8dd4jBKI9AhNC"

# If your jobs.employment_type / events.event_type are ENUMs, the generator checks
# these against the database and stops with a clear message if they don't match.
EMPLOYMENT_TYPES = ["Full-time", "Part-time", "Internship", "On-campus"]
EVENT_TYPES = ["Career Fair", "Workshop", "Info Session", "Networking", "Hackathon", "Panel"]

# Columns this script writes. If your schema names differ, change them here.
TABLE_COLUMNS = {
    "users": ["id", "email", "PASSWORD_COL", "role"],
    "student_profiles": ["id", "user_id", "full_name", "college_name", "career_objective", "city", "state",
                         "country", "degree", "major", "graduation_year", "cgpa", "experience", "skills", "phone"],
    "company_profiles": ["id", "user_id", "company_name", "location", "description", "contact_phone",
                         "profile_picture_url"],
    "jobs": ["id", "company_id", "title", "description", "company_name", "location", "city", "employment_type",
             "is_remote", "salary_min", "salary_max", "required_skills", "posted_at", "deadline"],
    "applications": ["id", "job_id", "student_id", "status", "applied_at", "resume_filename"],
    "events": ["id", "company_id", "title", "description", "organizer", "location", "city", "event_date",
               "event_type", "is_virtual", "capacity", "eligible_majors", "min_cgpa", "min_grad_year",
               "max_grad_year", "eligibility_note"],
    "event_registrations": ["id", "event_id", "student_id"],
}
PASSWORD_COLUMN_CANDIDATES = ["password_hash", "hashed_password", "password"]
INSERT_ORDER = ["users", "student_profiles", "company_profiles", "jobs", "applications", "events",
                "event_registrations"]
CLEAR_ORDER = ["assistant_tool_logs", "assistant_messages", "assistant_conversations", "saved_items",
               "event_registrations", "applications", "events", "jobs", "student_profiles",
               "company_profiles", "users"]

# ---------------------------------------------------------------- word lists
FIRST = ["Aiden", "Maya", "Liam", "Sofia", "Noah", "Priya", "Ethan", "Hana", "Lucas", "Amara", "Mateo", "Chloe",
         "Arjun", "Zoe", "Diego", "Mei", "Omar", "Ella", "Kenji", "Isla", "Samir", "Nora", "Tariq", "Lena",
         "Jordan", "Riya", "Caleb", "Yuki", "Felix", "Anya", "Marcus", "Dana", "Ravi", "Tessa", "Hugo", "Leila"]
LAST = ["Nguyen", "Patel", "Garcia", "Kim", "Chen", "Singh", "Lopez", "Tran", "Park", "Rivera", "Shah", "Lee",
        "Martinez", "Wong", "Ahmed", "Johnson", "Cho", "Reyes", "Gupta", "Kowalski", "Okafor", "Silva",
        "Tanaka", "Nakamura", "Hernandez", "Khan", "Morales", "Zhang", "Brown", "Ortiz"]
MAJORS = ["Computer Science", "Data Analytics", "Software Engineering", "Electrical Engineering",
          "Business Analytics", "Information Systems", "Mathematics", "Statistics"]
DEGREES = {"Computer Science": "B.S.", "Data Analytics": "M.S.", "Software Engineering": "B.S.",
           "Electrical Engineering": "B.S.", "Business Analytics": "M.S.", "Information Systems": "B.S.",
           "Mathematics": "B.S.", "Statistics": "M.S."}
COLLEGES = ["San Jose State University", "Santa Clara University", "De Anza College", "Foothill College",
            "Stanford University", "UC Santa Cruz"]
OTHER_CITIES = ["San Jose", "Santa Clara", "Milpitas", "Fremont"]
SKILLS = ["Python", "SQL", "FastAPI", "React", "JavaScript", "Java", "Docker", "AWS", "MySQL", "Spark",
          "Pandas", "Tableau", "Kafka", "Git", "Linux", "TypeScript", "Airflow", "Machine Learning",
          "Statistics", "Excel", "C++", "REST APIs", "PostgreSQL", "Kubernetes"]
COMPANY_A = ["Bright", "Blue", "Nimbus", "Vertex", "Orbit", "Quanta", "Lumen", "Summit", "Cobalt", "Pioneer",
             "Silver", "Apex", "Harbor", "Willow", "Ember", "Atlas", "Cedar", "Delta", "Echo", "Fable"]
COMPANY_B = ["Robotics", "Analytics", "Systems", "Labs", "Networks", "Cloud", "Health", "Logistics", "Energy",
             "Software", "Dynamics", "Data", "Security", "Mobility", "Media"]
JOB_TITLES = {
    "Internship": ["Data Engineering Intern", "Software Engineering Intern", "Data Analyst Intern",
                   "Machine Learning Intern", "Backend Developer Intern", "QA Automation Intern"],
    "Part-time": ["Part-time Data Analyst", "Part-time Web Developer", "IT Support Assistant",
                  "Part-time Research Assistant"],
    "On-campus": ["Campus Data Assistant", "Lab Technician", "Student Web Developer", "Library Systems Aide"],
    "Full-time": ["Data Engineer", "Software Engineer", "Backend Engineer", "Analytics Engineer",
                  "Cloud Engineer", "Data Scientist", "Frontend Engineer", "DevOps Engineer"],
}
SALARY_RANGE = {"Internship": (38000, 80000), "Part-time": (28000, 60000), "On-campus": (24000, 44000),
                "Full-time": (85000, 175000)}
EVENT_TITLES = {
    "Career Fair": ["Spring Career Fair", "Tech Career Fair", "Engineering Career Day"],
    "Workshop": ["Resume Workshop", "SQL Workshop", "Intro to Data Pipelines", "Cloud Basics Workshop",
                 "Git and Collaboration Workshop"],
    "Info Session": ["Company Info Session", "Internship Info Session", "New Grad Info Session"],
    "Networking": ["Alumni Networking Night", "Coffee and Careers", "Mentor Mixer"],
    "Hackathon": ["Data Hack Night", "Build Weekend"],
    "Panel": ["Women in Tech Panel", "Data Careers Panel", "Startup Founders Panel"],
}


# ---------------------------------------------------------------- generation
def _sample_skills(rng, k):
    return ", ".join(rng.sample(SKILLS, k))


def generate(seed=SEED):
    """Return {table_name: [row dict, ...]} with all ids assigned and all FKs valid."""
    rng = random.Random(seed)
    t = {name: [] for name in INSERT_ORDER}

    # --- companies: users 1..50, company_profiles 1..50
    used_names = set()
    for i in range(1, N_COMPANIES + 1):
        while True:
            name = f"{rng.choice(COMPANY_A)} {rng.choice(COMPANY_B)}"
            if name not in used_names:
                used_names.add(name)
                break
        slug = re.sub(r"[^a-z0-9]+", "", name.lower())
        city = rng.choice(CITY_SET)
        t["users"].append({"id": i, "email": f"hr+{slug}@companies.handshake-demo.com",
                           "PASSWORD_COL": SEED_PASSWORD_HASH, "role": "company"})
        t["company_profiles"].append({
            "id": i, "user_id": i, "company_name": name, "location": city,
            "description": f"{name} builds products for customers across the Bay Area and hires students "
                           f"who like working with data and software. Based in {city}.",
            "contact_phone": f"408-555-{1000 + i:04d}", "profile_picture_url": None})

    # --- students: users 51..250, student_profiles 1..200
    for i in range(1, N_STUDENTS + 1):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        major = rng.choice(MAJORS)
        grad = rng.choice([2026, 2027, 2027, 2028, 2028, 2029])
        city = rng.choice(CITY_SET) if rng.random() < 0.7 else rng.choice(OTHER_CITIES)
        skills = _sample_skills(rng, rng.randint(3, 6))
        uid = N_COMPANIES + i
        t["users"].append({"id": uid, "email": f"student{i}@students.handshake-demo.com",
                           "PASSWORD_COL": SEED_PASSWORD_HASH, "role": "student"})
        t["student_profiles"].append({
            "id": i, "user_id": uid, "full_name": f"{first} {last}", "college_name": rng.choice(COLLEGES),
            "career_objective": f"Seeking a role where I can apply {skills.split(', ')[0]} and "
                                f"{skills.split(', ')[1]} to real {major.lower()} problems.",
            "city": city, "state": "CA", "country": "USA", "degree": DEGREES[major], "major": major,
            "graduation_year": grad, "cgpa": round(rng.uniform(2.6, 4.0), 2),
            "experience": rng.choice(["No prior experience", "Course projects and one hackathon",
                                      "Campus IT assistant, 1 year", "Summer internship, 3 months",
                                      "Research assistant, 2 semesters"]),
            "skills": skills, "phone": f"669-555-{rng.randint(0, 9999):04d}"})

    # --- jobs: 300, exactly 6 per company (order shuffled)
    company_of_job = [1 + (j % N_COMPANIES) for j in range(N_JOBS)]
    rng.shuffle(company_of_job)
    jobs_by_id = {}
    for j in range(1, N_JOBS + 1):
        cid = company_of_job[j - 1]
        comp = t["company_profiles"][cid - 1]
        etype = rng.choices(EMPLOYMENT_TYPES, weights=[40, 15, 30, 15])[0]
        lo_s, hi_s = SALARY_RANGE[etype]
        smin = rng.randrange(lo_s, hi_s - 5000, 1000)
        smax = smin + rng.randrange(5, 31) * 1000
        remote = rng.random() < 0.2
        city = comp["location"] if rng.random() < 0.6 else rng.choice(CITY_SET)
        title = rng.choice(JOB_TITLES[etype])
        skills = _sample_skills(rng, rng.randint(3, 5))
        posted = ANCHOR - timedelta(days=rng.randint(0, 90), hours=rng.randint(0, 8))
        deadline = (posted + timedelta(days=rng.randint(14, 75))).date()
        row = {"id": j, "company_id": cid, "title": title,
               "description": f"{comp['company_name']} is hiring a {title.lower()} in {city}. You will work "
                              f"with {skills} on projects used by real customers. We value curiosity, "
                              f"clear communication and a willingness to learn.",
               "company_name": comp["company_name"], "location": f"{city}, CA", "city": city,
               "employment_type": etype, "is_remote": 1 if remote else 0, "salary_min": smin,
               "salary_max": smax, "required_skills": skills, "posted_at": posted.replace(microsecond=0),
               "deadline": deadline}
        t["jobs"].append(row)
        jobs_by_id[j] = row

    # --- applications: 1,500 unique (job, student) pairs
    pairs, app_id = set(), 0
    while app_id < N_APPLICATIONS:
        jid, sid = rng.randint(1, N_JOBS), rng.randint(1, N_STUDENTS)
        if (jid, sid) in pairs:
            continue
        pairs.add((jid, sid))
        app_id += 1
        job = jobs_by_id[jid]
        window_end = min(datetime.combine(job["deadline"], datetime.min.time()), ANCHOR)
        span = max(int((window_end - job["posted_at"]).total_seconds()), 3600)
        applied = job["posted_at"] + timedelta(seconds=rng.randrange(3600, span + 3600))
        applied = min(applied, ANCHOR)
        status = rng.choices(["Pending", "Reviewed", "Declined"], weights=[55, 30, 15])[0]
        first = t["student_profiles"][sid - 1]["full_name"].lower().replace(" ", "_")
        t["applications"].append({
            "id": app_id, "job_id": jid, "student_id": sid, "status": status,
            "applied_at": applied.replace(microsecond=0),
            "resume_filename": f"{first}_resume.pdf" if rng.random() < 0.8 else None})

    # --- events: 100 (about half the events are company-hosted by someone in the 50)
    for e in range(1, N_EVENTS + 1):
        cid = rng.randint(1, N_COMPANIES)
        comp = t["company_profiles"][cid - 1]
        etype = rng.choice(EVENT_TYPES)
        virtual = rng.random() < 0.25
        city = rng.choice(CITY_SET)
        when = ANCHOR + timedelta(days=rng.randint(-45, 75), hours=rng.choice([0, 1, 3, 5, 7]))
        majors = None
        if rng.random() < 0.35:
            majors = ", ".join(rng.sample(MAJORS, rng.randint(1, 3)))
        min_cgpa = rng.choice([2.5, 3.0, 3.5]) if rng.random() < 0.2 else None
        min_gy = rng.choice([2026, 2027]) if rng.random() < 0.15 else None
        max_gy = rng.choice([2027, 2028]) if (min_gy is None and rng.random() < 0.1) else None
        note_bits = []
        if majors:
            note_bits.append(f"Open to {majors} students")
        if min_cgpa:
            note_bits.append(f"minimum CGPA {min_cgpa}")
        title = f"{comp['company_name']} {rng.choice(EVENT_TITLES[etype])}"
        t["events"].append({
            "id": e, "company_id": cid, "title": title,
            "description": f"{etype} hosted by {comp['company_name']}. Meet the team, ask questions and "
                           f"learn what we look for in student candidates.",
            "organizer": comp["company_name"],
            "location": "Online" if virtual else f"{comp['company_name']} office, {city}, CA", "city": city,
            "event_date": when.replace(microsecond=0), "event_type": etype, "is_virtual": 1 if virtual else 0,
            "capacity": rng.choice([15, 25, 40, 60, 100]), "eligible_majors": majors, "min_cgpa": min_cgpa,
            "min_grad_year": min_gy, "max_grad_year": max_gy,
            "eligibility_note": "; ".join(note_bits) if note_bits else None})

    # --- registrations: eligible students only, never over capacity, no duplicates
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.services.eligibility import check_eligibility
    reg_id = 0
    for ev in t["events"]:
        want = rng.randint(3, min(ev["capacity"], 30))
        pool = list(range(1, N_STUDENTS + 1))
        rng.shuffle(pool)
        taken = 0
        for sid in pool:
            if taken >= want:
                break
            if check_eligibility(ev, t["student_profiles"][sid - 1])[0]:
                reg_id += 1
                taken += 1
                t["event_registrations"].append({"id": reg_id, "event_id": ev["id"], "student_id": sid})
    return t


# ---------------------------------------------------------------- self-check
def check_integrity(t):
    """Raise AssertionError if counts or foreign keys are wrong."""
    assert len(t["company_profiles"]) == N_COMPANIES
    assert len(t["student_profiles"]) == N_STUDENTS
    assert len(t["users"]) == N_COMPANIES + N_STUDENTS
    assert len(t["jobs"]) == N_JOBS and len(t["applications"]) == N_APPLICATIONS
    assert len(t["events"]) == N_EVENTS
    ids = lambda tbl: {r["id"] for r in t[tbl]}
    assert len(ids("users")) == len(t["users"])
    assert len({r["email"] for r in t["users"]}) == len(t["users"]), "duplicate emails"
    assert {r["user_id"] for r in t["student_profiles"]} | {r["user_id"] for r in t["company_profiles"]} == ids("users")
    assert all(r["company_id"] in ids("company_profiles") for r in t["jobs"] + t["events"])
    assert all(r["job_id"] in ids("jobs") and r["student_id"] in ids("student_profiles") for r in t["applications"])
    assert len({(r["job_id"], r["student_id"]) for r in t["applications"]}) == N_APPLICATIONS
    assert all(r["event_id"] in ids("events") and r["student_id"] in ids("student_profiles")
               for r in t["event_registrations"])
    assert len({(r["event_id"], r["student_id"]) for r in t["event_registrations"]}) == len(t["event_registrations"])
    caps = {e["id"]: e["capacity"] for e in t["events"]}
    counts = {}
    for r in t["event_registrations"]:
        counts[r["event_id"]] = counts.get(r["event_id"], 0) + 1
    assert all(c <= caps[e] for e, c in counts.items()), "over capacity"
    assert all(j["salary_min"] < j["salary_max"] and j["deadline"] >= j["posted_at"].date() for j in t["jobs"])
    assert all(j["city"] in CITY_SET for j in t["jobs"] + t["events"])
    assert all(a["applied_at"] >= jobs_posted(t, a["job_id"]) for a in t["applications"])


def jobs_posted(t, job_id):
    return t["jobs"][job_id - 1]["posted_at"]


# ---------------------------------------------------------------- output
def _sql_value(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, datetime):
        return "'" + v.strftime("%Y-%m-%d %H:%M:%S") + "'"
    if isinstance(v, date):
        return "'" + v.isoformat() + "'"
    s = str(v)
    assert "\\" not in s, "backslash in seed text would be read differently by MySQL"
    return "'" + s.replace("'", "''") + "'"


def to_sql(t, password_col="password_hash", include_clear=True):
    out = ["-- Generated by scripts/generate_seed_data.py (SEED=%d). Do not edit by hand." % SEED]
    if include_clear:
        out.append("SET FOREIGN_KEY_CHECKS=0;")
        out += [f"DELETE FROM {name};" for name in CLEAR_ORDER]
        out.append("SET FOREIGN_KEY_CHECKS=1;")
    for name in INSERT_ORDER:
        cols = [password_col if c == "PASSWORD_COL" else c for c in TABLE_COLUMNS[name]]
        keys = TABLE_COLUMNS[name]
        rows = t[name]
        for i in range(0, len(rows), 100):
            chunk = rows[i:i + 100]
            values = ",\n  ".join("(" + ", ".join(_sql_value(r[k]) for k in keys) + ")" for r in chunk)
            out.append(f"INSERT INTO {name} ({', '.join(cols)}) VALUES\n  {values};")
    return "\n".join(out) + "\n"


def _read_env(path):
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _connect_args(args):
    """Use flags, then DATABASE_URL from backend/.env, then DB_* environment variables."""
    from urllib.parse import urlparse, unquote
    env = {**_read_env(Path(__file__).resolve().parents[1] / ".env"), **os.environ}
    url = env.get("DATABASE_URL") or env.get("SQLALCHEMY_DATABASE_URL") or ""
    parsed = urlparse(url) if url else None
    return dict(
        host=args.host or (parsed.hostname if parsed else None) or env.get("DB_HOST", "127.0.0.1"),
        port=int(args.port or (parsed.port if parsed else None) or env.get("DB_PORT", 3306)),
        user=args.user or (unquote(parsed.username) if parsed and parsed.username else None) or env.get("DB_USER", "root"),
        password=args.password if args.password is not None else
        (unquote(parsed.password) if parsed and parsed.password else env.get("DB_PASSWORD", "")),
        database=args.database or (parsed.path.lstrip("/") if parsed and parsed.path else None) or env.get("DB_NAME", "p16_handshake"),
    )


def load_into_mysql(t, args):
    try:
        import pymysql
    except ImportError:
        sys.exit("pymysql is not installed. Activate the backend venv, or use --sql-out seed.sql instead.")
    conn = pymysql.connect(**_connect_args(args), charset="utf8mb4", autocommit=False)
    cur = conn.cursor()
    db = _connect_args(args)["database"]

    # 1. make sure the columns/enums we write really exist
    cur.execute("SELECT table_name, column_name, column_type FROM information_schema.columns "
                "WHERE table_schema=%s", (db,))
    have = {}
    for tbl, col, ctype in cur.fetchall():
        have.setdefault(tbl, {})[col] = ctype
    pw = next((c for c in PASSWORD_COLUMN_CANDIDATES if c in have.get("users", {})), None)
    problems = []
    if pw is None:
        problems.append(f"users has none of {PASSWORD_COLUMN_CANDIDATES}")
    for tbl, cols in TABLE_COLUMNS.items():
        if tbl not in have:
            problems.append(f"table {tbl} is missing (did you run database/05_company_workflow.sql?)")
            continue
        for c in cols:
            if c != "PASSWORD_COL" and c not in have[tbl]:
                problems.append(f"{tbl}.{c} is missing")
    for tbl, col, allowed in (("jobs", "employment_type", EMPLOYMENT_TYPES), ("events", "event_type", EVENT_TYPES)):
        ctype = have.get(tbl, {}).get(col, "")
        if ctype.lower().startswith("enum("):
            values = re.findall(r"'((?:[^']|'')*)'", ctype)
            bad = [v for v in allowed if v not in values]
            if bad:
                problems.append(f"{tbl}.{col} is {ctype}; edit the list at the top of this script (not allowed: {bad})")
    if problems:
        sys.exit("Schema doesn't match what the generator writes:\n  - " + "\n  - ".join(problems))

    # 2. clear and insert
    try:
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        for name in CLEAR_ORDER:
            if name in have:
                cur.execute(f"DELETE FROM {name}")
        for name in INSERT_ORDER:
            keys = TABLE_COLUMNS[name]
            cols = [pw if c == "PASSWORD_COL" else c for c in keys]
            sql = f"INSERT INTO {name} ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})"
            cur.executemany(sql, [tuple(r[k] for k in keys) for r in t[name]])
        cur.execute("SET FOREIGN_KEY_CHECKS=1")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def summary(t):
    return "\n".join(f"{name:22s} {len(t[name]):5d}" for name in INSERT_ORDER)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reset", action="store_true", help="empty the tables and load the seed data into MySQL")
    ap.add_argument("--sql-out", metavar="FILE", help="write the seed as a .sql file instead of using the database")
    ap.add_argument("--password-column", default="password_hash", help="users password column for --sql-out")
    ap.add_argument("--summary", action="store_true", help="print row counts only")
    for flag in ("host", "port", "user", "password", "database"):
        ap.add_argument("--" + flag)
    args = ap.parse_args()

    data = generate()
    check_integrity(data)
    print(summary(data))
    if args.sql_out:
        Path(args.sql_out).write_text(to_sql(data, args.password_column))
        print("wrote", args.sql_out)
    if args.reset:
        load_into_mysql(data, args)
        print(f"loaded. Log in as student1@students.handshake-demo.com / {SEED_PASSWORD}")
    if not (args.reset or args.sql_out or args.summary):
        ap.print_help()


if __name__ == "__main__":
    main()
