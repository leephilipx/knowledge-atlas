import sqlite3
import json
from datetime import datetime
import uuid
from typing import List, Optional, Tuple
import pandas as pd

DB_FILE = "repository.db"

def get_db_connection():
    """Returns a connection object to the SQLite database."""
    return sqlite3.connect(DB_FILE)

def init_db():
    """Initializes the main entries table and the FTS5 virtual table."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Main Entries Table (Transactional data and current metadata)
    c.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id TEXT PRIMARY KEY,
            theme TEXT,
            source_type TEXT,
            source_url TEXT,
            entry_date TEXT,
            process_stage TEXT,
            tags TEXT,
            summary_caption TEXT,
            explain_like_im_5 TEXT,
            file_storage_path TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    ''')
    
    # 2. FTS5 Virtual Table (Search index for summaries)
    # The 'content' column is optional but links the index to the main table.
    # We index 'summary_caption' and link by 'id'.
    c.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
            id UNINDEXED, 
            summary_caption, 
            content='entries', 
            content_rowid='id'
        );
    ''')

    # 3. Triggers to keep FTS table synchronized with 'entries'
    # Triggers ensure FTS5 index updates whenever an entry is added or changed.
    c.execute('''
        CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
            INSERT INTO entries_fts(id, summary_caption) VALUES (new.id, new.summary_caption);
        END;
    ''')
    
    c.execute('''
        CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE ON entries BEGIN
            UPDATE entries_fts SET summary_caption = new.summary_caption WHERE id = new.id;
        END;
    ''')

    # Note: DELETE trigger is omitted for brevity but recommended in production.
    
    conn.commit()
    conn.close()

# --- Core CRUD Functions (Updated to handle FTS synchronization via triggers) ---

def add_entry(entry_data: dict) -> str:
    """Inserts a new entry into the main table and triggers FTS indexing."""
    conn = get_db_connection()
    c = conn.cursor()
    
    new_id = str(uuid.uuid4())
    now = datetime.now()
    
    c.execute('''
        INSERT INTO entries (
            id, theme, source_type, source_url, entry_date, 
            process_stage, created_at, updated_at, summary_caption
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        new_id,
        entry_data.get('theme', 'General'),
        entry_data['source_type'],
        entry_data['source_url'],
        entry_data.get('entry_date', str(now.strftime("%Y-%m"))),
        'Uploaded',
        now,
        now,
        'Processing summary...' # Placeholder summary, updated by worker later
    ))
    conn.commit()
    conn.close()
    return new_id

def update_status(entry_id: str, stage: str, result_data: Optional[dict] = None):
    """Update stage and optionally save LLM results, triggering FTS update."""
    conn = get_db_connection()
    c = conn.cursor()
    
    now = datetime.now()
    query = "UPDATE entries SET process_stage = ?, updated_at = ?"
    params: List[any] = [stage, now]

    if result_data:
        if 'summary_caption' in result_data:
            query += ", summary_caption = ?"
            params.append(result_data['summary_caption'])
        if 'explain_like_im_5' in result_data:
            query += ", explain_like_im_5 = ?"
            params.append(result_data['explain_like_im_5'])
        if 'tags' in result_data:
            query += ", tags = ?"
            params.append(json.dumps(result_data['tags']))
        if 'file_storage_path' in result_data:
            query += ", file_storage_path = ?"
            params.append(result_data['file_storage_path'])

    query += " WHERE id = ?"
    params.append(entry_id)
    
    c.execute(query, tuple(params))
    conn.commit()
    conn.close()

def get_entry(entry_id: str) -> Optional[dict]:
    # ... (Implementation remains the same)
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


# --- New Search and Pagination Methods ---

def search_entries(keyword: str) -> List[str]:
    """Uses FTS5 to find entry IDs matching the keyword."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # FTS5 MATCH query for prefix searching (e.g., 'art*' finds 'artist', 'artistic')
    # The double quotes ensure the phrase is treated as a token set.
    query = "SELECT id FROM entries_fts WHERE summary_caption MATCH ?"
    c.execute(query, (f'{keyword}*',))
    
    # Extract IDs from the results
    matching_ids = [row[0] for row in c.fetchall()]
    conn.close()
    return matching_ids


def get_paginated_entries(
    page: int, 
    limit: int, 
    matching_ids: Optional[List[str]] = None
) -> Tuple[pd.DataFrame, int]:
    """
    Fetches a single page of data, optionally filtered by IDs, 
    and returns the total count for pagination.
    """
    conn = get_db_connection()
    offset = (page - 1) * limit
    
    # Base query for data retrieval
    data_query = "SELECT * FROM entries"
    
    # Base query for total count (for pagination metadata)
    count_query = "SELECT COUNT(id) FROM entries"
    
    where_clause = ""
    params: List[any] = []
    
    if matching_ids:
        # Create a string of placeholders (?, ?, ?) for the IN clause
        placeholders = ', '.join(['?'] * len(matching_ids))
        where_clause = f" WHERE id IN ({placeholders})"
        params.extend(matching_ids)

    # --- Execute Count Query ---
    final_count_query = count_query + where_clause
    total_count = conn.execute(final_count_query, params).fetchone()[0]
    
    # --- Execute Data Query with Pagination ---
    # Apply ordering and LIMIT/OFFSET for the specific page
    final_data_query = (
        data_query + 
        where_clause + 
        " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
    )
    
    # Add LIMIT and OFFSET to the parameters for the final execution
    data_params = params + [limit, offset]
    
    df = pd.read_sql_query(final_data_query, conn, params=data_params)
    
    conn.close()
    
    return df, total_count