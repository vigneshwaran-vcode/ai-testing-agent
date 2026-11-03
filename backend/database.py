import sqlite3
import json
from datetime import datetime
from config import Config

def get_db():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Model configurations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS model_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            model_id TEXT NOT NULL,
            display_name TEXT,
            api_key_ref TEXT,
            base_url TEXT,
            capabilities TEXT,  -- JSON list
            is_active INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    ''')

    # Test sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_name TEXT,
            model_config_id INTEGER,
            provider TEXT,
            model_id TEXT,
            status TEXT DEFAULT 'pending',  -- pending, running, completed, failed
            total_tests INTEGER DEFAULT 0,
            passed_tests INTEGER DEFAULT 0,
            failed_tests INTEGER DEFAULT 0,
            avg_response_time REAL DEFAULT 0,
            overall_score REAL DEFAULT 0,
            reliability_level TEXT DEFAULT 'UNKNOWN',
            capabilities_tested TEXT,  -- JSON list
            started_at TEXT,
            completed_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (model_config_id) REFERENCES model_configs(id)
        )
    ''')

    # Test cases
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            capability TEXT NOT NULL,
            subcategory TEXT,
            difficulty TEXT DEFAULT 'normal',  -- normal, hard, edge_case
            prompt TEXT NOT NULL,
            expected_output TEXT,
            evaluation_criteria TEXT,  -- JSON
            status TEXT DEFAULT 'pending',  -- pending, running, passed, failed, skipped
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES test_sessions(id)
        )
    ''')

    # Test results
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_case_id INTEGER,
            session_id INTEGER,
            capability TEXT,
            model_response TEXT,
            response_time_ms REAL,
            score REAL,  -- 0-100
            status TEXT,  -- correct, partially_correct, incorrect, unsupported, failed, review_needed
            metrics TEXT,  -- JSON: capability-specific metrics
            failures TEXT,  -- JSON: detected failure details
            evidence TEXT,  -- JSON: supporting evidence
            severity TEXT,  -- low, medium, high, critical
            confidence REAL,  -- 0-100 confidence in evaluation
            recommendation TEXT,
            executed_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (test_case_id) REFERENCES test_cases(id),
            FOREIGN KEY (session_id) REFERENCES test_sessions(id)
        )
    ''')

    # Capability scores (aggregated per session)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS capability_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            capability TEXT NOT NULL,
            total_tests INTEGER DEFAULT 0,
            passed_tests INTEGER DEFAULT 0,
            avg_score REAL DEFAULT 0,
            avg_response_time REAL DEFAULT 0,
            failure_count INTEGER DEFAULT 0,
            reliability_level TEXT,
            details TEXT,  -- JSON
            FOREIGN KEY (session_id) REFERENCES test_sessions(id)
        )
    ''')

    # Settings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    ''')

    conn.commit()
    conn.close()
    print("[DB] Database initialized successfully.")

# ── Helper functions ──────────────────────────────────────────────────────────

def get_setting(key, default=None):
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row['value'] if row else default

def set_setting(key, value):
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        (key, value)
    )
    conn.commit()
    conn.close()

def get_active_model():
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM model_configs WHERE is_active=1 ORDER BY updated_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def set_active_model(model_id):
    conn = get_db()
    conn.execute("UPDATE model_configs SET is_active=0")
    conn.execute(
        "UPDATE model_configs SET is_active=1, updated_at=datetime('now') WHERE id=?",
        (model_id,)
    )
    conn.commit()
    conn.close()

def create_session(model_config_id, provider, model_id, session_name=None):
    conn = get_db()
    if not session_name:
        session_name = f"{provider}/{model_id} — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    cursor = conn.execute(
        '''INSERT INTO test_sessions (model_config_id, provider, model_id, session_name, status, started_at)
           VALUES (?, ?, ?, ?, 'running', datetime('now'))''',
        (model_config_id, provider, model_id, session_name)
    )
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id

def get_session(session_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM test_sessions WHERE id=?", (session_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_sessions():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM test_sessions ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_session_results(session_id):
    conn = get_db()
    rows = conn.execute(
        '''SELECT tr.*, tc.prompt, tc.capability, tc.subcategory, tc.difficulty, tc.expected_output
           FROM test_results tr
           JOIN test_cases tc ON tr.test_case_id = tc.id
           WHERE tr.session_id=?
           ORDER BY tr.executed_at''',
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_capability_scores(session_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM capability_scores WHERE session_id=?", (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_model_config(provider, model_id, display_name, api_key_ref='', base_url='', capabilities=None):
    conn = get_db()
    caps_json = json.dumps(capabilities or [])
    cursor = conn.execute(
        '''INSERT OR REPLACE INTO model_configs
           (provider, model_id, display_name, api_key_ref, base_url, capabilities, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, datetime('now'))''',
        (provider, model_id, display_name, api_key_ref, base_url, caps_json)
    )
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id

def get_all_models():
    conn = get_db()
    rows = conn.execute("SELECT * FROM model_configs ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]
