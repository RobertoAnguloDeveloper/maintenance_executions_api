from app import db
from app.models.token_blocklist import TokenBlocklist
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

def cleanup_token_blocklist():
    """
    Remove tokens from blocklist that are older than 7 days.
    This should be run as a scheduled task.
    """
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
        deleted_count = db.session.query(TokenBlocklist).filter(
            TokenBlocklist.created_at < cutoff_date
        ).delete()
        db.session.commit()
        logger.info(f"Removed {deleted_count} expired tokens from blocklist")
        return deleted_count
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error cleaning up token blocklist: {str(e)}")
        return 0