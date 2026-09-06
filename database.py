import sqlite3
import os
from typing import List, Dict, Any, Optional

class DICOMDatabase:
    def __init__(self, db_path: str = "dicom_studies.db"):
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Table for DICOM Studies
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS studies (
                    study_instance_uid TEXT PRIMARY KEY,
                    patient_id TEXT,
                    patient_name TEXT,
                    patient_sex TEXT,
                    patient_birth_date TEXT,
                    study_date TEXT,
                    study_time TEXT,
                    study_description TEXT,
                    modalities TEXT,
                    accession_number TEXT,
                    num_series INTEGER DEFAULT 0,
                    num_instances INTEGER DEFAULT 0
                )
            """)

            # Table for DICOM Series
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS series (
                    series_instance_uid TEXT PRIMARY KEY,
                    study_instance_uid TEXT,
                    series_number INTEGER,
                    series_description TEXT,
                    modality TEXT,
                    body_part_examined TEXT,
                    num_instances INTEGER DEFAULT 0,
                    FOREIGN KEY(study_instance_uid) REFERENCES studies(study_instance_uid) ON DELETE CASCADE
                )
            """)

            # Table for DICOM Instances / Slices
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS instances (
                    sop_instance_uid TEXT PRIMARY KEY,
                    series_instance_uid TEXT,
                    study_instance_uid TEXT,
                    instance_number INTEGER,
                    file_path TEXT UNIQUE,
                    slice_location REAL,
                    rows INTEGER,
                    columns INTEGER,
                    FOREIGN KEY(series_instance_uid) REFERENCES series(series_instance_uid) ON DELETE CASCADE,
                    FOREIGN KEY(study_instance_uid) REFERENCES studies(study_instance_uid) ON DELETE CASCADE
                )
            """)

            # Indexes for ultra-fast natural language and filter queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_studies_patient_name ON studies(patient_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_studies_patient_id ON studies(patient_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_studies_study_date ON studies(study_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_series_modality ON series(modality)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_series_study_uid ON series(study_instance_uid)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_instances_series_uid ON instances(series_instance_uid)")
            conn.commit()

    def upsert_study(self, study_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO studies (
                    study_instance_uid, patient_id, patient_name, patient_sex,
                    patient_birth_date, study_date, study_time, study_description,
                    modalities, accession_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(study_instance_uid) DO UPDATE SET
                    patient_id=excluded.patient_id,
                    patient_name=excluded.patient_name,
                    patient_sex=excluded.patient_sex,
                    patient_birth_date=excluded.patient_birth_date,
                    study_date=excluded.study_date,
                    study_time=excluded.study_time,
                    study_description=excluded.study_description,
                    modalities=excluded.modalities,
                    accession_number=excluded.accession_number
            """, (
                study_data["study_instance_uid"],
                study_data.get("patient_id", "UNKNOWN"),
                study_data.get("patient_name", "ANONYMOUS"),
                study_data.get("patient_sex", "U"),
                study_data.get("patient_birth_date", ""),
                study_data.get("study_date", ""),
                study_data.get("study_time", ""),
                study_data.get("study_description", "No Description"),
                study_data.get("modalities", ""),
                study_data.get("accession_number", "")
            ))
            conn.commit()

    def upsert_series(self, series_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO series (
                    series_instance_uid, study_instance_uid, series_number,
                    series_description, modality, body_part_examined
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(series_instance_uid) DO UPDATE SET
                    series_number=excluded.series_number,
                    series_description=excluded.series_description,
                    modality=excluded.modality,
                    body_part_examined=excluded.body_part_examined
            """, (
                series_data["series_instance_uid"],
                series_data["study_instance_uid"],
                series_data.get("series_number", 1),
                series_data.get("series_description", "Series"),
                series_data.get("modality", "OT"),
                series_data.get("body_part_examined", "")
            ))
            conn.commit()

    def upsert_instance(self, instance_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO instances (
                    sop_instance_uid, series_instance_uid, study_instance_uid,
                    instance_number, file_path, slice_location, rows, columns
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(sop_instance_uid) DO UPDATE SET
                    file_path=excluded.file_path,
                    instance_number=excluded.instance_number,
                    slice_location=excluded.slice_location,
                    rows=excluded.rows,
                    columns=excluded.columns
            """, (
                instance_data["sop_instance_uid"],
                instance_data["series_instance_uid"],
                instance_data["study_instance_uid"],
                instance_data.get("instance_number", 1),
                instance_data["file_path"],
                instance_data.get("slice_location", 0.0),
                instance_data.get("rows", 512),
                instance_data.get("columns", 512)
            ))
            conn.commit()

    def update_counts(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Update study counts and distinct modalities
            cursor.execute("""
                UPDATE series SET num_instances = (
                    SELECT COUNT(*) FROM instances WHERE instances.series_instance_uid = series.series_instance_uid
                )
            """)
            cursor.execute("""
                UPDATE studies SET
                    num_series = (SELECT COUNT(*) FROM series WHERE series.study_instance_uid = studies.study_instance_uid),
                    num_instances = (SELECT COUNT(*) FROM instances WHERE instances.study_instance_uid = studies.study_instance_uid),
                    modalities = (
                        SELECT GROUP_CONCAT(DISTINCT modality) FROM series WHERE series.study_instance_uid = studies.study_instance_uid
                    )
            """)
            conn.commit()

    def query_studies(self, sql_where: str = "", params: tuple = ()) -> List[Dict[str, Any]]:
        query = """
            SELECT
                s.study_instance_uid,
                s.patient_id,
                s.patient_name,
                s.patient_sex,
                s.patient_birth_date,
                s.study_date,
                s.study_time,
                s.study_description,
                s.modalities,
                s.accession_number,
                s.num_series,
                s.num_instances
            FROM studies s
        """
        if sql_where:
            query += f" WHERE {sql_where}"
        query += " ORDER BY s.study_date DESC, s.study_time DESC"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_study_instances(self, study_instance_uid: str) -> List[Dict[str, Any]]:
        query = """
            SELECT i.sop_instance_uid, i.series_instance_uid, i.instance_number, i.file_path, i.slice_location, se.modality, se.series_description
            FROM instances i
            JOIN series se ON i.series_instance_uid = se.series_instance_uid
            WHERE i.study_instance_uid = ?
            ORDER BY se.series_number ASC, i.instance_number ASC, i.slice_location ASC
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (study_instance_uid,))
            return [dict(row) for row in cursor.fetchall()]

    def clear(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM instances")
            cursor.execute("DELETE FROM series")
            cursor.execute("DELETE FROM studies")
            conn.commit()
