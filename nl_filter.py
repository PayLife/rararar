import re
import datetime
from typing import Dict, Any, Tuple, List

class NaturalLanguageFilter:
    """Parses natural language medical search queries into structured SQL clauses and params."""

    MODALITY_MAP = {
        'ct': 'CT',
        'computed tomography': 'CT',
        'mri': 'MR',
        'mr': 'MR',
        'magnetic resonance': 'MR',
        'xray': 'CR',
        'x-ray': 'CR',
        'cr': 'CR',
        'radiograph': 'CR',
        'ultrasound': 'US',
        'us': 'US',
        'echo': 'US',
        'pet': 'PT',
        'nuclear': 'PT',
    }

    BODY_PARTS = [
        'chest', 'brain', 'head', 'abdomen', 'pelvis', 'spine',
        'knee', 'shoulder', 'heart', 'cardiac', 'lung', 'liver'
    ]

    def __init__(self):
        pass

    def parse(self, query: str) -> Tuple[str, List[Any], Dict[str, Any]]:
        """
        Parses query string like 'CT Chest from last week' or 'MR Brain 2023'.
        Returns (sql_where_clause, sql_params, extracted_tokens)
        """
        if not query or not query.strip():
            return "", [], {}

        q = query.strip().lower()
        sql_conditions = []
        params = []
        tokens = {}

        # 1. Modality Extraction
        found_modality = None
        for key, mod in self.MODALITY_MAP.items():
            pattern = r'\b' + re.escape(key) + r'\b'
            if re.search(pattern, q):
                found_modality = mod
                q = re.sub(pattern, '', q).strip()
                break

        if found_modality:
            tokens['modality'] = found_modality
            # Match in studies.modalities OR series.modality
            sql_conditions.append("""
                s.study_instance_uid IN (
                    SELECT study_instance_uid FROM series WHERE modality = ?
                )
            """)
            params.append(found_modality)

        # 2. Date / Relative Time Parsing
        today = datetime.date.today()
        date_from = None
        date_to = None

        if 'today' in q:
            date_from = today
            date_to = today
            q = q.replace('today', '').strip()
            tokens['time_frame'] = 'Today'
        elif 'yesterday' in q:
            date_from = today - datetime.timedelta(days=1)
            date_to = date_from
            q = q.replace('yesterday', '').strip()
            tokens['time_frame'] = 'Yesterday'
        elif 'last week' in q or 'past week' in q or 'recent' in q:
            date_from = today - datetime.timedelta(days=7)
            date_to = today
            q = re.sub(r'last week|past week|recent', '', q).strip()
            tokens['time_frame'] = 'Last 7 Days'
        elif 'last month' in q or 'past month' in q:
            date_from = today - datetime.timedelta(days=30)
            date_to = today
            q = re.sub(r'last month|past month', '', q).strip()
            tokens['time_frame'] = 'Last 30 Days'
        elif 'last year' in q:
            date_from = today - datetime.timedelta(days=365)
            date_to = today
            q = q.replace('last year', '').strip()
            tokens['time_frame'] = 'Last Year'
        else:
            # Check for explicit 4-digit year e.g., 2023
            year_match = re.search(r'\b(20\d\d|19\d\d)\b', q)
            if year_match:
                yr = int(year_match.group(1))
                date_from = datetime.date(yr, 1, 1)
                date_to = datetime.date(yr, 12, 31)
                q = q.replace(year_match.group(1), '').strip()
                tokens['time_frame'] = str(yr)

        if date_from and date_to:
            sql_conditions.append("s.study_date >= ? AND s.study_date <= ?")
            params.append(date_from.strftime("%Y%m%d"))
            params.append(date_to.strftime("%Y%m%d"))

        # Clean filler words ('from', 'for', 'scan', 'study', 'examination', 'with', 'and')
        q = re.sub(r'\b(from|for|scan|study|examination|exam|with|and|in)\b', '', q).strip()
        q = re.sub(r'\s+', ' ', q)

        # 3. Remaining Text - Fuzzy match across Patient Name, Patient ID, Study Description
        if q:
            tokens['free_text'] = q
            like_pattern = f"%{q}%"
            sql_conditions.append("""
                (s.patient_name LIKE ? OR s.patient_id LIKE ? OR s.study_description LIKE ? OR
                 s.study_instance_uid IN (SELECT study_instance_uid FROM series WHERE series_description LIKE ? OR body_part_examined LIKE ?))
            """)
            params.extend([like_pattern, like_pattern, like_pattern, like_pattern, like_pattern])

        where_clause = " AND ".join(f"({c})" for c in sql_conditions) if sql_conditions else ""
        return where_clause, params, tokens
