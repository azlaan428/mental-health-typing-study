from flask import Flask, request, jsonify, render_template, send_from_directory
import mysql.connector
import uuid
import base64
import os
from datetime import datetime

app = Flask(__name__)

# ─────────────────────────────────────────
# MySQL config - set these as environment variables on Render
# ─────────────────────────────────────────
DB_CONFIG = {
    "host":     os.environ.get("MYSQL_HOST"),
    "port":     int(os.environ.get("MYSQL_PORT", 23634)),
    "user":     os.environ.get("MYSQL_USER"),
    "password": os.environ.get("MYSQL_PASSWORD"),
    "database": os.environ.get("MYSQL_DATABASE", "defaultdb"),
    "ssl_ca":   os.environ.get("MYSQL_SSL_CA", "ca.pem"),
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit():
    try:
        data = request.get_json()

        participant_id = data["participant_id"]
        session_id     = data["session_id"]
        ip_address     = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
        now            = datetime.now()

        conn   = get_db()
        cursor = conn.cursor()

        # participants
        cursor.execute("""
            INSERT INTO participants
                (participant_id, session_id, ip_address, age, gender,
                 year_of_study, consent_timestamp, data_version, collection_date)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            participant_id, session_id, ip_address,
            data["age"], data["gender"], data["year_of_study"],
            now, "v2", now
        ))

        # phq9
        cursor.execute("""
            INSERT INTO phq9_responses
                (participant_id, phq9_total, phq9_severity, depression_label,
                 q1,q2,q3,q4,q5,q6,q7,q8,q9)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            participant_id,
            data["phq9_total"], data["phq9_severity"],
            1 if data["phq9_total"] >= 10 else 0,
            *data["phq9_scores"]
        ))

        # typing
        cursor.execute("""
            INSERT INTO typing_data
                (participant_id,
                 copy_task_duration, copy_task_word_count, copy_task_char_count, copy_task_text,
                 free_writing_duration, free_writing_word_count, free_writing_char_count, free_writing_text)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            participant_id,
            data["copy_duration"],
            len(data["copy_text"].split()),
            len(data["copy_text"]),
            data["copy_text"],
            data["free_duration"],
            len(data["free_text"].split()),
            len(data["free_text"]),
            data["free_text"],
        ))

        # consent record with screenshot
        cursor.execute("""
            INSERT INTO consent_records
                (participant_id, session_id, ip_address, consent_timestamp,
                 screenshot_base64, data_version, notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            participant_id, session_id, ip_address, now,
            data.get("consent_screenshot"),
            "v2", None
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "ok"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
