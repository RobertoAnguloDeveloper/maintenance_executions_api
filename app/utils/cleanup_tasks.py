# In app/utils/cleanup_tasks.py
from app import db
from app.models.token_blocklist import TokenBlocklist
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

def cleanup_token_blocklist(days=7):
    """Remove tokens from blocklist that are older than specified days."""
    try:
        # Calculate cutoff time
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Delete old records in chunks to avoid locking the table for too long
        chunk_size = 1000
        total_deleted = 0
        
        while True:
            # Get batch of IDs to delete
            to_delete = db.session.query(TokenBlocklist.id).filter(
                TokenBlocklist.created_at < cutoff_date
            ).limit(chunk_size).all()
            
            if not to_delete:
                break
                
            # Extract just the IDs
            id_list = [item[0] for item in to_delete]
            
            # Delete this batch
            deleted = db.session.query(TokenBlocklist).filter(
                TokenBlocklist.id.in_(id_list)
            ).delete(synchronize_session=False)
            
            db.session.commit()
            total_deleted += deleted
            
            # If we got fewer records than chunk_size, we're done
            if len(id_list) < chunk_size:
                break
        
        logger.info(f"Removed {total_deleted} expired tokens from blocklist")
        return total_deleted
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error cleaning up token blocklist: {str(e)}")
        return 0