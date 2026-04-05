"""
export_to_csv.py
Exports MySQL data to all_participant_data.csv in the same format
as the original Google Sheets export, so csv_feature_extraction.py works unchanged.

Usage:
    python export_to_csv.py
"""

import mysql.connector
import pandas as pd
import os

DB_CONFIG = {
    "host":     "mysql-2f7ea6c7-azlaanmohammad95-9df7.a.aivencloud.com",
    "port":     23634,
    "user":     "avnadmin",
    "password": "AVNS_C9VnxHefp8Lvg4yeZax",
    "database": "defaultdb",
    "ssl_ca":   "ca.pem",
}

def export():
    conn   = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            p.participant_id,
            p.age,
            p.gender,
            p.year_of_study,
            q.phq9_total,
            q.phq9_severity,
            q.depression_label,
            q.q1  AS phq9_q1,
            q.q2  AS phq9_q2,
            q.q3  AS phq9_q3,
            q.q4  AS phq9_q4,
            q.q5  AS phq9_q5,
            q.q6  AS phq9_q6,
            q.q7  AS phq9_q7,
            q.q8  AS phq9_q8,
            q.q9  AS phq9_q9,
            t.copy_task_duration,
            t.copy_task_word_count,
            t.copy_task_char_count,
            t.free_writing_duration,
            t.free_writing_word_count,
            t.free_writing_char_count,
            t.copy_task_text,
            t.free_writing_text,
            p.collection_date
        FROM participants p
        JOIN phq9_responses q ON p.participant_id = q.participant_id
        JOIN typing_data    t ON p.participant_id = t.participant_id
        ORDER BY p.collection_date
    """)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    df = pd.DataFrame(rows)
    df.rename(columns={"collection_date": "collection_date"}, inplace=True)
    df.to_csv("all_participant_data.csv", index=False)
    print(f"Exported {len(df)} rows to all_participant_data.csv")

if __name__ == "__main__":
    export()
