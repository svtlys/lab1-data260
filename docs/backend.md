\# Backend Documentation



\## Project configuration



\- Pair: 16

\- Backend port: 9160

\- Database: p16\_handshake

\- Database prefix: p16

\- Seed: 16

\- City set:

&#x20; - Sunnyvale

&#x20; - Cupertino

&#x20; - Mountain View



\## Backend technologies



\- Python

\- FastAPI

\- Uvicorn

\- SQLAlchemy

\- MySQL

\- PyMySQL

\- Bcrypt

\- JWT

\- Pydantic



\## Backend folder structure



```text

backend/

├── app/

│   ├── api/

│   │   ├── dependencies.py

│   │   └── routes/

│   │       ├── auth.py

│   │       └── student\_profile.py

│   ├── core/

│   │   ├── config.py

│   │   ├── database.py

│   │   └── security.py

│   ├── models/

│   │   ├── user.py

│   │   ├── student\_profile.py

│   │   └── company\_profile.py

│   ├── schemas/

│   │   ├── auth.py

│   │   └── student\_profile.py

│   └── main.py

├── tests/

└── requirements.txt

