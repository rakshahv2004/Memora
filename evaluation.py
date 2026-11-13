import sqlite3
from datetime import datetime

DB_NAME = "memora.db"


def initialize_evaluation_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            response TEXT,
            mode TEXT NOT NULL,
            latency REAL NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS experiment_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            memory_mode TEXT NOT NULL,
            relevance INTEGER NOT NULL,
            personalization INTEGER NOT NULL,
            accuracy INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("PRAGMA table_info(experiment_ratings)")
    columns = [column[1] for column in cursor.fetchall()]

    if "experiment_id" not in columns:
        cursor.execute(
            "ALTER TABLE experiment_ratings ADD COLUMN experiment_id TEXT"
        )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS experiment_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id TEXT NOT NULL,
            question TEXT NOT NULL,
            memory_on_response TEXT NOT NULL,
            memory_off_response TEXT NOT NULL,
            model TEXT,
            prompt_version TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(experiment_id, question)
        )
    """)

    conn.commit()
    conn.close()


def save_evaluation(question, response, mode, latency):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO evaluation_logs
        (question, response, mode, latency, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        question,
        response,
        mode,
        latency,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def get_evaluation_logs():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, question, response, mode, latency, created_at
        FROM evaluation_logs
        ORDER BY id DESC
    """)

    logs = cursor.fetchall()
    conn.close()
    return logs


def save_experiment_rating(
    question,
    memory_mode,
    relevance,
    personalization,
    accuracy,
    experiment_id
):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO experiment_ratings
        (question, memory_mode, relevance, personalization,
         accuracy, created_at, experiment_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        question,
        memory_mode,
        relevance,
        personalization,
        accuracy,
        datetime.now().isoformat(),
        experiment_id
    ))

    conn.commit()
    conn.close()


def get_experiment_ratings():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, question, memory_mode,
               relevance, personalization, accuracy,
               created_at, experiment_id
        FROM experiment_ratings
        ORDER BY id DESC
    """)

    ratings = cursor.fetchall()
    conn.close()
    return ratings


def save_experiment_pair(
    experiment_id,
    question,
    memory_on_response,
    memory_off_response,
    model=None,
    prompt_version=None
):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO experiment_pairs (
            experiment_id,
            question,
            memory_on_response,
            memory_off_response,
            model,
            prompt_version,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(experiment_id, question)
        DO UPDATE SET
            memory_on_response = excluded.memory_on_response,
            memory_off_response = excluded.memory_off_response,
            model = excluded.model,
            prompt_version = excluded.prompt_version,
            created_at = excluded.created_at
    """, (
        experiment_id,
        question,
        memory_on_response,
        memory_off_response,
        model,
        prompt_version,
        datetime.now().isoformat()
    ))

    conn.commit()
    saved_id = cursor.lastrowid
    conn.close()
    return saved_id


def get_experiment_pairs(experiment_id=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if experiment_id:
        cursor.execute("""
            SELECT id, experiment_id, question,
                   memory_on_response, memory_off_response,
                   model, prompt_version, created_at
            FROM experiment_pairs
            WHERE experiment_id = ?
            ORDER BY id DESC
        """, (experiment_id,))
    else:
        cursor.execute("""
            SELECT id, experiment_id, question,
                   memory_on_response, memory_off_response,
                   model, prompt_version, created_at
            FROM experiment_pairs
            ORDER BY id DESC
        """)

    pairs = cursor.fetchall()
    conn.close()
    return pairs


initialize_evaluation_database()
