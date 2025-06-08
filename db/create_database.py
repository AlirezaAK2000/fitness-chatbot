import sqlite3

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
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Create user_progress table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_progress (
        progress_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id       INTEGER NOT NULL
                        REFERENCES users(user_id) ON DELETE CASCADE,
        log_date      DATE    NOT NULL,
        entry_type    TEXT    NOT NULL
                        CHECK(entry_type IN (
                            'weight_check',
                            'meal',
                            'workout',
                            'note'
                        )),
        details       TEXT    NOT NULL,
        created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, log_date, entry_type)
    );
    """)

    conn.commit()
    conn.close()

    print(f"SQLite database '{db_path}' created/verified with updated schema.") 
