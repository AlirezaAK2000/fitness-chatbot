from werkzeug.security import generate_password_hash
import sqlite3
import json
import secrets

DB_PATH = 'fitness.db'

def create_database(db_path: str = DB_PATH):
    # Connect to SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create users table, now with an optional designed_plan field
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
        email           TEXT    NOT NULL UNIQUE,
        password_hash   TEXT    NOT NULL,
        first_name      TEXT,
        last_name       TEXT,
        date_of_birth   DATE,
        sex             TEXT    CHECK (sex IN ('M','F','O')),
        height_cm       REAL,
        weight_kg       REAL,
        activity_level  TEXT,
        dietary_pref    TEXT,
        fitness_goals   TEXT,
        designed_plan   TEXT,              -- optional chatbot‐generated plan
        auth_token      TEXT UNIQUE,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Create user_progress table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_progress (
        progress_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id       INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        details       TEXT    NOT NULL,
        created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()

    print(f"SQLite database '{db_path}' created/verified with updated schema.") 


def insert_dummy_data(db_mg):

    with open("data/users.json", 'r') as f:
        users = json.loads(json.load(f))
    with open("data/logs.json", 'r') as f:
        logs = json.load(f)


    for i, (user, log) in enumerate(zip(users['users'], logs)):
        db_mg.create_user(
            email = user['email'],
            password_hash = generate_password_hash(user['password']),
            first_name = user['first_name'],
            last_name = user['last_name'],
            date_of_birth = user['date_of_birth'],
            sex =  user['sex'],
            height_cm = user['height_cm'],
            weight_kg = user['weight_kg'],
            activity_level = user['activity_level'],
            dietary_pref = user['dietary_pref'],
            fitness_goals = user['fitness_goals'],
        )

        for l in log:
            db_mg.create_progress_entry(i + 1 , l)

        token = secrets.token_urlsafe(32)
        db_mg.set_auth_token(i + 1 , token)