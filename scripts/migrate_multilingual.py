"""Reset database for schema migration and re-summarize all papers.

Run this script once after updating to the multilingual schema.
It will:
1. Drop old summary column (if exists)
2. Create new summary_json column
3. Create users table
4. Reset all summaries to force re-summarization
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.storage import get_engine, get_session, init_db, PaperRepository


def migrate_database():
    """Perform database migration for multilingual support."""
    print("🔄 Starting database migration...")
    
    engine = get_engine()
    
    with engine.connect() as conn:
        # Check if old 'summary' column exists
        try:
            result = conn.execute(text("SELECT summary FROM papers LIMIT 1"))
            has_old_summary = True
            print("  Found old 'summary' column")
        except Exception:
            has_old_summary = False
            print("  No old 'summary' column found")
        
        # Check if new 'summary_json' column exists
        try:
            result = conn.execute(text("SELECT summary_json FROM papers LIMIT 1"))
            has_new_summary = True
            print("  Found 'summary_json' column")
        except Exception:
            has_new_summary = False
            print("  No 'summary_json' column found")
        
        # Add summary_json column if not exists
        if not has_new_summary:
            print("  Adding 'summary_json' column...")
            conn.execute(text("ALTER TABLE papers ADD COLUMN summary_json TEXT"))
            conn.commit()
            print("  ✓ Added 'summary_json' column")
        
        # Drop old summary column if exists (SQLite doesn't support DROP COLUMN easily)
        # So we'll just leave it and ignore it
        
    # Reinitialize with new schema (creates users table)
    print("  Initializing new schema (users table)...")
    init_db()
    print("  ✓ Schema initialized")
    
    # Reset all summaries
    print("  Resetting all summaries for re-summarization...")
    session = get_session()
    repo = PaperRepository(session)
    count = repo.reset_all_summaries()
    session.close()
    print(f"  ✓ Reset {count} papers for re-summarization")
    
    print("✅ Migration complete! Restart the bot to begin re-summarization.")


if __name__ == "__main__":
    migrate_database()
