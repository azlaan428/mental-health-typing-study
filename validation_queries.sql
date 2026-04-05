-- ═══════════════════════════════════════════════════════════
-- Validation Queries for Mental Health Typing Study Database
-- Run these in MySQL Workbench after connecting to Aiven.
-- ═══════════════════════════════════════════════════════════


-- 1. Total responses by data version (v1 = migrated, v2 = new)
SELECT data_version, COUNT(*) AS total
FROM participants
GROUP BY data_version;


-- 2. All participants overview
SELECT p.participant_id, p.age, p.gender, p.year_of_study,
       p.ip_address, p.session_id, p.data_version, p.collection_date,
       q.phq9_total, q.phq9_severity, q.depression_label
FROM participants p
JOIN phq9_responses q ON p.participant_id = q.participant_id
ORDER BY p.collection_date;


-- 3. Check for duplicate IP addresses (potential bias indicator)
SELECT ip_address, COUNT(*) AS submissions
FROM participants
WHERE ip_address IS NOT NULL
GROUP BY ip_address
HAVING COUNT(*) > 1
ORDER BY submissions DESC;


-- 4. Check for duplicate session IDs (should be zero for v2)
SELECT session_id, COUNT(*) AS submissions
FROM participants
WHERE session_id IS NOT NULL
GROUP BY session_id
HAVING COUNT(*) > 1;


-- 5. Geographic/network distribution of v2 participants
SELECT ip_address, COUNT(*) AS count
FROM participants
WHERE data_version = 'v2'
GROUP BY ip_address
ORDER BY count DESC;


-- 6. PHQ-9 severity distribution
SELECT phq9_severity, COUNT(*) AS count,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM phq9_responses), 1) AS percentage
FROM phq9_responses
GROUP BY phq9_severity
ORDER BY FIELD(phq9_severity, 'Minimal','Mild','Moderate','Moderately Severe','Severe');


-- 7. Depression label breakdown
SELECT depression_label,
       CASE WHEN depression_label = 1 THEN 'Depressed' ELSE 'Not Depressed' END AS label,
       COUNT(*) AS count
FROM phq9_responses
GROUP BY depression_label;


-- 8. Demographics: gender distribution
SELECT gender, COUNT(*) AS count
FROM participants
GROUP BY gender;


-- 9. Demographics: year of study distribution
SELECT year_of_study, COUNT(*) AS count
FROM participants
GROUP BY year_of_study
ORDER BY year_of_study;


-- 10. Typing speed comparison by depression label
SELECT q.depression_label,
       ROUND(AVG(t.copy_task_word_count / (t.copy_task_duration / 60)), 1) AS avg_copy_wpm,
       ROUND(AVG(t.free_writing_word_count / (t.free_writing_duration / 60)), 1) AS avg_free_wpm
FROM typing_data t
JOIN phq9_responses q ON t.participant_id = q.participant_id
WHERE t.copy_task_duration > 0 AND t.free_writing_duration > 0
GROUP BY q.depression_label;


-- 11. Consent records audit (v2 should all have screenshots)
SELECT data_version,
       COUNT(*) AS total,
       SUM(CASE WHEN screenshot_base64 IS NOT NULL THEN 1 ELSE 0 END) AS with_screenshot,
       SUM(CASE WHEN screenshot_base64 IS NULL THEN 1 ELSE 0 END) AS without_screenshot
FROM consent_records
GROUP BY data_version;


-- 12. Full data export (all tables joined)
SELECT p.participant_id, p.session_id, p.ip_address, p.age, p.gender,
       p.year_of_study, p.data_version, p.collection_date,
       q.phq9_total, q.phq9_severity, q.depression_label,
       q.q1, q.q2, q.q3, q.q4, q.q5, q.q6, q.q7, q.q8, q.q9,
       t.copy_task_duration, t.copy_task_word_count, t.copy_task_char_count,
       t.free_writing_duration, t.free_writing_word_count, t.free_writing_char_count
FROM participants p
JOIN phq9_responses q  ON p.participant_id = q.participant_id
JOIN typing_data t     ON p.participant_id = t.participant_id
ORDER BY p.collection_date;
