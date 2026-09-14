import os
import sys
import json
import psycopg2

def upload_to_db(scan_id, repo, filepath):
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set")
        sys.exit(1)
        
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to load json: {e}")
        sys.exit(1)
        
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO demo_scans (scan_id, repo_url, status, raw_json_output)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (scan_id) DO UPDATE 
            SET status = EXCLUDED.status, raw_json_output = EXCLUDED.raw_json_output
        """, (scan_id, repo, "COMPLETED", json.dumps(data)))
        print(f"Successfully uploaded scan {scan_id} to database.")
    except Exception as e:
        print(f"Database insert failed: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python db_upload.py <scan_id> <repo> <filepath>")
        sys.exit(1)
    upload_to_db(sys.argv[1], sys.argv[2], sys.argv[3])
