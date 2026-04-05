"""
Migration script: loads existing CSV data into MySQL database.
Run once after setting up your Aiven MySQL instance.

Usage:
    python migrate.py

Make sure to fill in your Aiven credentials in the config section below.
"""

import mysql.connector
import pandas as pd
import sys

# ─────────────────────────────────────────
# CONFIG: Fill these in with your Aiven credentials
# ─────────────────────────────────────────
DB_CONFIG = {
    "host":     "xxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "port":     23634,
    "user":     "avnadmin",
    "password": "xxxxxxxxxxxxxxxxxxx",
    "database": "defaultdb",
    "ssl_ca":   "ca.pem",
}

CSV_PATH = "all_participant_data.csv"   # path to your exported CSV
# ─────────────────────────────────────────


CREATE_PARTICIPANTS = """
CREATE TABLE IF NOT EXISTS participants (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    participant_id      VARCHAR(20) UNIQUE NOT NULL,
    session_id          VARCHAR(60),
    ip_address          VARCHAR(60),
    age                 INT,
    gender              VARCHAR(30),
    year_of_study       VARCHAR(10),
    consent_timestamp   DATETIME,
    data_version        VARCHAR(5) DEFAULT 'v1',
    collection_date     DATETIME,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_PHQ9 = """
CREATE TABLE IF NOT EXISTS phq9_responses (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    participant_id      VARCHAR(20) NOT NULL,
    phq9_total          INT,
    phq9_severity       VARCHAR(30),
    depression_label    TINYINT,
    q1                  INT, q2 INT, q3 INT, q4 INT, q5 INT,
    q6                  INT, q7 INT, q8 INT, q9 INT,
    FOREIGN KEY (participant_id) REFERENCES participants(participant_id)
);
"""

CREATE_TYPING = """
CREATE TABLE IF NOT EXISTS typing_data (
    id                          INT AUTO_INCREMENT PRIMARY KEY,
    participant_id              VARCHAR(20) NOT NULL,
    copy_task_duration          FLOAT,
    copy_task_word_count        INT,
    copy_task_char_count        INT,
    copy_task_text              TEXT,
    free_writing_duration       FLOAT,
    free_writing_word_count     INT,
    free_writing_char_count     INT,
    free_writing_text           TEXT,
    FOREIGN KEY (participant_id) REFERENCES participants(participant_id)
);
"""

CREATE_CONSENT = """
CREATE TABLE IF NOT EXISTS consent_records (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    participant_id      VARCHAR(20) NOT NULL,
    session_id          VARCHAR(60),
    ip_address          VARCHAR(60),
    consent_timestamp   DATETIME,
    screenshot_base64   LONGTEXT,
    data_version        VARCHAR(5) DEFAULT 'v1',
    notes               TEXT,
    FOREIGN KEY (participant_id) REFERENCES participants(participant_id)
);
"""


def connect():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print("Connected to MySQL successfully.")
        return conn
    except mysql.connector.Error as e:
        print(f"Connection failed: {e}")
        sys.exit(1)


def create_tables(cursor):
    for ddl in [CREATE_PARTICIPANTS, CREATE_PHQ9, CREATE_TYPING, CREATE_CONSENT]:
        cursor.execute(ddl)
    print("Tables created (or already exist).")


def migrate(cursor, df):
    inserted = 0
    skipped = 0

    for _, row in df.iterrows():
        pid = str(row["participant_id"]).strip()

        # Check for duplicate
        cursor.execute("SELECT id FROM participants WHERE participant_id = %s", (pid,))
        if cursor.fetchone():
            print(f"  Skipping duplicate: {pid}")
            skipped += 1
            continue

        # participants
        cursor.execute("""
            INSERT INTO participants
                (participant_id, session_id, ip_address, age, gender,
                 year_of_study, consent_timestamp, data_version, collection_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            pid,
            None,                          # no session_id for v1
            None,                          # no ip_address for v1
            int(row["age"]),
            str(row["gender"]),
            str(row["year_of_study"]),
            None,                          # no consent_timestamp for v1
            "v1",
            str(row["collection_date"])[:19] if pd.notna(row["collection_date"]) else None
        ))

        # phq9_responses
        cursor.execute("""
            INSERT INTO phq9_responses
                (participant_id, phq9_total, phq9_severity, depression_label,
                 q1, q2, q3, q4, q5, q6, q7, q8, q9)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            pid,
            int(row["phq9_total"]),
            str(row["phq9_severity"]),
            int(row["depression_label"]),
            int(row["phq9_q1"]), int(row["phq9_q2"]), int(row["phq9_q3"]),
            int(row["phq9_q4"]), int(row["phq9_q5"]), int(row["phq9_q6"]),
            int(row["phq9_q7"]), int(row["phq9_q8"]), int(row["phq9_q9"])
        ))

        # typing_data
        cursor.execute("""
            INSERT INTO typing_data
                (participant_id,
                 copy_task_duration, copy_task_word_count, copy_task_char_count, copy_task_text,
                 free_writing_duration, free_writing_word_count, free_writing_char_count, free_writing_text)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            pid,
            float(row["copy_task_duration"]) if pd.notna(row["copy_task_duration"]) else None,
            int(row["copy_task_word_count"]) if pd.notna(row["copy_task_word_count"]) else None,
            int(row["copy_task_char_count"]) if pd.notna(row["copy_task_char_count"]) else None,
            str(row["copy_task_text"]) if pd.notna(row["copy_task_text"]) else None,
            float(row["free_writing_duration"]) if pd.notna(row["free_writing_duration"]) else None,
            int(row["free_writing_word_count"]) if pd.notna(row["free_writing_word_count"]) else None,
            int(row["free_writing_char_count"]) if pd.notna(row["free_writing_char_count"]) else None,
            str(row["free_writing_text"]) if pd.notna(row["free_writing_text"]) else None,
        ))

        # consent_records (v1 note)
        cursor.execute("""
            INSERT INTO consent_records
                (participant_id, session_id, ip_address, consent_timestamp,
                 screenshot_base64, data_version, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            pid, None, None, None, None, "v1",
            "Consent obtained via checkbox. No screenshot available for pre-v2 submissions."
        ))

        inserted += 1

    print(f"Migration complete: {inserted} inserted, {skipped} skipped.")


def main():
    df = pd.read_csv(CSV_PATH)
    print(f"Loaded CSV: {len(df)} rows.")

    conn = connect()
    cursor = conn.cursor()

    create_tables(cursor)
    migrate(cursor, df)

    conn.commit()
    cursor.close()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
