"""
Migration script to create new budget tables.
Run from backend/ directory: python scripts/migrate_budget_tables.py
"""

from sqlalchemy import create_engine
from pathlib import Path
import sys
import logging

# Add src to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from receipt_story.db.tables import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Create all budget-related tables"""
    
    # Get database path
    backend_dir = Path(__file__).parent.parent
    db_path = backend_dir / "data" / "receipts.db"
    
    logger.info(f"Database path: {db_path}")
    logger.info(f"Database exists: {db_path.exists()}")
    
    if not db_path.exists():
        logger.error(f"Database not found at {db_path}")
        return
    
    # Create engine
    db_url = f"sqlite:///{db_path.absolute()}"
    engine = create_engine(db_url, echo=True)
    
    # Create all tables
    logger.info("Creating new tables...")
    Base.metadata.create_all(engine)
    
    logger.info("✅ Migration complete!")


if __name__ == "__main__":
    run_migration()