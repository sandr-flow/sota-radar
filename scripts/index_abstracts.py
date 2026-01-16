"""Script to index existing paper abstracts into ChromaDB.

Run this once to populate the 'abstracts' collection for Smart Chat.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select

from src.config.settings import settings
from src.rag.vector_store import VectorStore
from src.storage import session_scope
from src.storage.models import PaperModel


def main():
    """Index all paper abstracts."""
    print("Starting abstract indexing...")
    
    vector_store = VectorStore()
    count = 0
    skipped = 0
    errors = 0
    
    with session_scope() as session:
        # Get all papers
        stmt = select(PaperModel)
        result = session.execute(stmt)
        papers = result.scalars().all()
        
        total = len(papers)
        print(f"Found {total} papers in database.")
        
        for paper in papers:
            try:
                if not paper.abstract:
                    skipped += 1
                    continue
                    
                # Index abstract
                success = vector_store.add_abstract(
                    paper_id=paper.source_id,
                    title=paper.title,
                    abstract=paper.abstract
                )
                
                if success:
                    count += 1
                    if count % 10 == 0:
                        print(f"Indexed {count}/{total} papers...", end="\r")
                else:
                    skipped += 1
                    
            except Exception as e:
                print(f"Error indexing paper {paper.id}: {e}")
                errors += 1
                
    print(f"\nDone! Indexed: {count}, Skipped: {skipped}, Errors: {errors}")


if __name__ == "__main__":
    main()
