import sqlite3
import os
from typing import Optional, List, Dict, Any
from db.create_database import create_database, DB_PATH, insert_dummy_data

class FitnessDB:
    def __init__(self, db_path: str = DB_PATH, use_dummy_data = True):
        # Ensure database file exists; create schema if not
        self.db_path = db_path
        if not os.path.exists(self.db_path):
            create_database(self.db_path)
            if use_dummy_data:
                insert_dummy_data(self)

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_user(self, email: str, password_hash: str, first_name: Optional[str] = None,
                    last_name: Optional[str] = None, date_of_birth: Optional[str] = None,
                    sex: Optional[str] = None, height_cm: Optional[float] = None,
                    weight_kg: Optional[float] = None, activity_level: Optional[str] = None,
                    dietary_pref: Optional[str] = None, fitness_goals: Optional[str] = None) -> int:
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (email, password_hash, first_name, last_name, date_of_birth,
                               sex, height_cm, weight_kg, activity_level, dietary_pref, fitness_goals)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (email, password_hash, first_name, last_name, date_of_birth,
              sex, height_cm, weight_kg, activity_level, dietary_pref, fitness_goals))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row is not None else None

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row is not None else None

    def update_user(self, user_id: int, **fields) -> bool:
        """
        Updates specified fields for the given user_id.
        Returns True if at least one row was updated.
        """
        if not fields:
            return False
        columns = ", ".join([f"{key} = ?" for key in fields.keys()])
        values = list(fields.values()) + [user_id]
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET {columns}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", values)
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated

    def delete_user(self, user_id: int) -> bool:
        """
        Deletes a user by user_id.
        Returns True if a row was deleted.
        """
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    # -------------------------
    # Progress Log CRUD Operations
    # -------------------------

    def create_progress_entry(self, user_id: int, log_date: str, entry_type: str, details: str) -> int:
        """
        Inserts a new progress entry and returns the new progress_id.
        """
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_progress (user_id, log_date, entry_type, details)
            VALUES (?, ?, ?, ?)
        """, (user_id, log_date, entry_type, details))
        conn.commit()
        progress_id = cursor.lastrowid
        conn.close()
        return progress_id

    def get_progress_by_user(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves all progress entries for a user.
        """
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_progress WHERE user_id = ? ORDER BY log_date DESC", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_progress_entry(self, progress_id: int, **fields) -> bool:
        """
        Updates specified fields for the given progress_id.
        Returns True if at least one row was updated.
        """
        if not fields:
            return False
        columns = ", ".join([f"{key} = ?" for key in fields.keys()])
        values = list(fields.values()) + [progress_id]
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE user_progress SET {columns} WHERE progress_id = ?", values)
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated

    def delete_progress_entry(self, progress_id: int) -> bool:
        """
        Deletes a progress entry by progress_id.
        Returns True if a row was deleted.
        """
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_progress WHERE progress_id = ?", (progress_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def get_last_progress(self, user_id: int, num_logs = 3) -> List[Dict[str, Any]]:
        """
        Retrieves the last `num_logs` progress entries for a given user, ordered by log_date descending.
        """
        conn = self._connect
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT progress_id, user_id, log_date, entry_type, details, created_at
            FROM user_progress
            WHERE user_id = ?
            ORDER BY log_date DESC, created_at DESC
            LIMIT ?
        """, (user_id, num_logs))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def set_user_plan(self, user_id: int, plan: str) -> bool:
        """
        Sets or updates the chatbot-designed plan for a user.
        Returns True if the update affected a row.
        """
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET designed_plan = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (plan, user_id)
        )
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated

    def get_user_plan(self, user_id: int) -> Optional[str]:
        """
        Retrieves the chatbot-designed plan for a user, or None if not set.
        """
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT designed_plan FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row["designed_plan"] if row is not None else None