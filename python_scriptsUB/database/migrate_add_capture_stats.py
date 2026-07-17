"""
Database Migration Script
Add near_pass_count to tbl_sessions and create tbl_capture_sessions

Run this script on Ubuntu server:
    cd ~/pse-vision/python_scripts
    python3 database/migrate_add_capture_stats.py
"""

import sqlite3
import sys
from pathlib import Path

def migrate_database(db_path='data/pse_vision.db'):
    """Add capture statistics support to existing database"""
    
    print(f"🔄 Starting database migration...")
    print(f"📁 Database: {db_path}")
    
    try:
        # Check if database exists
        db_file = Path(db_path)
        if not db_file.exists():
            print(f"⚠️  Database file not found: {db_path}")
            print(f"✅ This is OK - new database will be created automatically on first run")
            return True
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n📊 Checking current schema...")
        
        # Check if tbl_sessions exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='tbl_sessions'
        """)
        sessions_table_exists = cursor.fetchone() is not None
        
        if sessions_table_exists:
            # Check if near_pass_count column exists
            cursor.execute("PRAGMA table_info(tbl_sessions)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'near_pass_count' not in columns:
                print("➕ Adding 'near_pass_count' column to tbl_sessions...")
                cursor.execute("""
                    ALTER TABLE tbl_sessions 
                    ADD COLUMN near_pass_count INTEGER DEFAULT 0
                """)
                print("   ✅ Column added successfully")
            else:
                print("   ℹ️  Column 'near_pass_count' already exists")
        else:
            print("   ℹ️  Table 'tbl_sessions' does not exist (will be created automatically)")
        
        # Check if tbl_capture_sessions exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='tbl_capture_sessions'
        """)
        captures_table_exists = cursor.fetchone() is not None
        
        if not captures_table_exists:
            print("➕ Creating 'tbl_capture_sessions' table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tbl_capture_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    capture_id TEXT UNIQUE NOT NULL,
                    machine_id TEXT,
                    machine_name TEXT,
                    lot_id TEXT,
                    lot_name TEXT,
                    lot_type TEXT,
                    rubber_type TEXT,
                    image_path TEXT,
                    captured_at TEXT NOT NULL,
                    total_detected INTEGER DEFAULT 0,
                    pass_count INTEGER DEFAULT 0,
                    near_pass_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("   ✅ Table created successfully")
        else:
            print("   ℹ️  Table 'tbl_capture_sessions' already exists")
        
        # Commit changes
        conn.commit()
        
        # Verify migration
        print("\n🔍 Verifying migration...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"   Tables found: {', '.join(tables)}")
        
        # Close connection
        cursor.close()
        conn.close()
        
        print("\n✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    # Get database path from command line or use default
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'data/pse_vision.db'
    
    success = migrate_database(db_path)
    sys.exit(0 if success else 1)
