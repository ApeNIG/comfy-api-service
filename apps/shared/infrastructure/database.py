"""
Database infrastructure - SQLAlchemy setup with connection pooling

Usage:
    from apps.shared.infrastructure.database import get_db, engine

    # In FastAPI route:
    @router.get("/users")
    def get_users(db: Session = Depends(get_db)):
        return db.query(User).all()
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
import structlog

from config import settings

logger = structlog.get_logger(__name__)

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.DATABASE_ECHO,  # Log SQL queries in debug
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class for all models
Base = declarative_base()


# Event listeners for connection lifecycle
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Called when a new DB connection is created"""
    logger.debug("database_connection_created")


@event.listens_for(engine, "close")
def receive_close(dbapi_conn, connection_record):
    """Called when a DB connection is closed"""
    logger.debug("database_connection_closed")


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI routes to get database session.

    Automatically handles:
    - Session creation
    - Transaction commit on success
    - Rollback on error
    - Session cleanup

    Usage:
        @router.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("database_transaction_failed", error=str(e))
        raise
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables.

    Usage:
        # Run once on app startup
        from apps.shared.infrastructure.database import init_db
        init_db()
    """
    logger.info("database_initializing")
    Base.metadata.create_all(bind=engine)
    logger.info("database_initialized")


def close_db():
    """
    Close all database connections.

    Usage:
        # Run on app shutdown
        from apps.shared.infrastructure.database import close_db
        close_db()
    """
    logger.info("database_closing_connections")
    engine.dispose()
    logger.info("database_connections_closed")


# Context manager for transactions
class db_transaction:
    """
    Context manager for database transactions outside of FastAPI.

    Usage:
        from apps.shared.infrastructure.database import db_transaction

        with db_transaction() as db:
            user = db.query(User).first()
            user.name = "Updated"
            # Automatically commits on success, rolls back on error
    """

    def __enter__(self) -> Session:
        self.db = SessionLocal()
        return self.db

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.db.commit()
        else:
            self.db.rollback()
            logger.error(
                "database_transaction_rolled_back",
                error_type=exc_type.__name__,
                error=str(exc_val)
            )
        self.db.close()
