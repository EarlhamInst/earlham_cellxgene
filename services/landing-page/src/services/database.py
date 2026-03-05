"""
SQLite Database Service

Manages SQLite database connections, schema creation, and migrations.

Constitutional Alignment:
- Principle II (Modular Architecture): Isolated database management
- Principle IV (Fail-Fast): Validates database on startup
- Principle III (Code Clarity): Clear API for database operations
"""

import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Generator
from datetime import datetime


class DatabaseError(Exception):
    """Raised when database operations fail."""
    pass


# Current schema version - increment when making schema changes
CURRENT_SCHEMA_VERSION = 1


# Schema definition for version 1
SCHEMA_V1 = """
-- Users table (ORCID-authenticated users)
CREATE TABLE IF NOT EXISTS users (
    orcid_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    email TEXT,
    created_at TEXT NOT NULL,
    last_login_at TEXT NOT NULL,
    storage_quota_bytes INTEGER DEFAULT 53687091200,
    storage_used_bytes INTEGER DEFAULT 0
);

-- Datasets table (both curated and user-uploaded)
CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT,
    organism TEXT DEFAULT 'Unknown',
    tissue TEXT DEFAULT 'Unknown',
    assay TEXT DEFAULT 'Unknown',
    cell_count INTEGER,
    gene_count INTEGER,
    file_size_bytes INTEGER,
    doi TEXT,
    publication TEXT,
    owner_orcid TEXT,
    visibility TEXT DEFAULT 'public' CHECK(visibility IN ('public', 'unlisted', 'private')),
    source TEXT DEFAULT 'curated' CHECK(source IN ('curated', 'user_upload')),
    is_valid BOOLEAN DEFAULT 1,
    validation_errors TEXT,
    additional_metadata TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    view_count INTEGER DEFAULT 0,
    FOREIGN KEY (owner_orcid) REFERENCES users(orcid_id)
);

CREATE INDEX IF NOT EXISTS idx_datasets_owner ON datasets(owner_orcid);
CREATE INDEX IF NOT EXISTS idx_datasets_visibility ON datasets(visibility);
CREATE INDEX IF NOT EXISTS idx_datasets_source ON datasets(source);

-- Access grants (email-verified access to private datasets)
CREATE TABLE IF NOT EXISTS access_grants (
    id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    email TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    verified BOOLEAN DEFAULT 0,
    verified_at TEXT,
    revoked BOOLEAN DEFAULT 0,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_grants_email ON access_grants(email);
CREATE INDEX IF NOT EXISTS idx_grants_dataset ON access_grants(dataset_id);

-- Access log (tracks grant usage)
CREATE TABLE IF NOT EXISTS access_grant_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grant_id TEXT NOT NULL,
    accessed_at TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    FOREIGN KEY (grant_id) REFERENCES access_grants(id) ON DELETE CASCADE
);

-- Shareable links (token-based access)
CREATE TABLE IF NOT EXISTS shareable_links (
    id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    created_by_orcid TEXT,
    created_by_email TEXT,
    label TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    max_uses INTEGER,
    use_count INTEGER DEFAULT 0,
    last_used_at TEXT,
    revoked BOOLEAN DEFAULT 0,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_orcid) REFERENCES users(orcid_id)
);

CREATE INDEX IF NOT EXISTS idx_links_token ON shareable_links(token_hash);
CREATE INDEX IF NOT EXISTS idx_links_dataset ON shareable_links(dataset_id);

-- Shareable link access log
CREATE TABLE IF NOT EXISTS shareable_link_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link_id TEXT NOT NULL,
    accessed_at TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    FOREIGN KEY (link_id) REFERENCES shareable_links(id) ON DELETE CASCADE
);

-- Schema version for migrations
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT
);
"""


class Database:
    """
    SQLite database manager with connection pooling and schema management.
    
    Thread-safe: Uses separate connections per context.
    For in-memory databases (:memory:), uses a shared connection since
    SQLite in-memory DBs are per-connection.
    """
    
    def __init__(self, db_path: Path, logger: Optional[logging.Logger] = None):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file (or ":memory:" for in-memory)
            logger: Optional logger instance
        """
        self.db_path = Path(db_path) if str(db_path) != ":memory:" else db_path
        self.logger = logger or logging.getLogger(__name__)
        self._initialized = False
        self._is_memory = str(db_path) == ":memory:"
        self._shared_conn = None  # For in-memory databases
    
    def initialize(self) -> None:
        """
        Initialize database, creating schema if needed.
        
        Should be called once on application startup.
        """
        if self._initialized:
            return
        
        # Ensure parent directory exists (skip for in-memory)
        if not self._is_memory:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Initializing database at: {self.db_path}")
        
        with self.get_connection() as conn:
            # Check if this is a fresh database
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
            )
            schema_exists = cursor.fetchone() is not None
            
            if not schema_exists:
                self.logger.info("Creating fresh database schema (version 1)")
                self._create_schema(conn)
            else:
                # Check version and migrate if needed
                current_version = self._get_schema_version(conn)
                if current_version < CURRENT_SCHEMA_VERSION:
                    self.logger.info(
                        f"Migrating database from version {current_version} to {CURRENT_SCHEMA_VERSION}"
                    )
                    self._migrate(conn, current_version)
                else:
                    self.logger.info(f"Database schema is up to date (version {current_version})")
        
        self._initialized = True
        self.logger.info("Database initialization complete")
    
    def _create_schema(self, conn: sqlite3.Connection) -> None:
        """Create the initial database schema."""
        conn.executescript(SCHEMA_V1)
        
        # Record schema version
        conn.execute(
            "INSERT INTO schema_version (version, applied_at, description) VALUES (?, ?, ?)",
            (1, datetime.utcnow().isoformat(), "Initial schema with user uploads support")
        )
        conn.commit()
    
    def _get_schema_version(self, conn: sqlite3.Connection) -> int:
        """Get current schema version."""
        cursor = conn.execute("SELECT MAX(version) FROM schema_version")
        result = cursor.fetchone()
        return result[0] if result and result[0] else 0
    
    def _migrate(self, conn: sqlite3.Connection, from_version: int) -> None:
        """
        Run migrations from from_version to CURRENT_SCHEMA_VERSION.
        
        Add migration functions here as schema evolves.
        """
        # Example migration pattern for future versions:
        # if from_version < 2:
        #     self._migrate_v1_to_v2(conn)
        # if from_version < 3:
        #     self._migrate_v2_to_v3(conn)
        pass
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with proper settings."""
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            isolation_level=None,  # Autocommit mode, use explicit transactions
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Get a database connection as a context manager.
        
        For in-memory databases, returns a shared connection that stays open.
        For file databases, creates a new connection each time.
        
        Yields:
            SQLite connection with row factory set to sqlite3.Row
            
        Usage:
            with db.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM users")
                rows = cursor.fetchall()
        """
        if self._is_memory:
            # In-memory: use shared connection (don't close it)
            if self._shared_conn is None:
                self._shared_conn = self._create_connection()
            yield self._shared_conn
        else:
            # File-based: create new connection each time
            conn = self._create_connection()
            try:
                yield conn
            finally:
                conn.close()
    
    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Execute operations within a transaction.
        
        Automatically commits on success, rolls back on exception.
        
        Yields:
            SQLite connection within a transaction
            
        Usage:
            with db.transaction() as conn:
                conn.execute("INSERT INTO users ...")
                conn.execute("INSERT INTO datasets ...")
                # Commits automatically on exit
        """
        with self.get_connection() as conn:
            conn.execute("BEGIN")
            try:
                yield conn
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
    
    def execute(
        self, 
        sql: str, 
        params: tuple = ()
    ) -> List[sqlite3.Row]:
        """
        Execute a query and return all results.
        
        Args:
            sql: SQL query
            params: Query parameters
            
        Returns:
            List of Row objects
        """
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchall()
    
    def execute_one(
        self, 
        sql: str, 
        params: tuple = ()
    ) -> Optional[sqlite3.Row]:
        """
        Execute a query and return first result.
        
        Args:
            sql: SQL query
            params: Query parameters
            
        Returns:
            Single Row object or None
        """
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchone()
    
    def execute_write(
        self, 
        sql: str, 
        params: tuple = ()
    ) -> int:
        """
        Execute a write operation (INSERT, UPDATE, DELETE).
        
        Args:
            sql: SQL statement
            params: Statement parameters
            
        Returns:
            Number of rows affected
        """
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor.rowcount
    
    def execute_insert(
        self, 
        sql: str, 
        params: tuple = ()
    ) -> int:
        """
        Execute an INSERT and return the last row ID.
        
        Args:
            sql: INSERT statement
            params: Statement parameters
            
        Returns:
            Last inserted row ID
        """
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor.lastrowid
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get column information for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column info dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.execute(f"PRAGMA table_info({table_name})")
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    "cid": row[0],
                    "name": row[1],
                    "type": row[2],
                    "notnull": bool(row[3]),
                    "default": row[4],
                    "pk": bool(row[5]),
                })
            return columns
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            return cursor.fetchone() is not None
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with counts for each table
        """
        stats = {}
        tables = ["users", "datasets", "access_grants", "shareable_links"]
        
        with self.get_connection() as conn:
            for table in tables:
                if self.table_exists(table):
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[table] = cursor.fetchone()[0]
                else:
                    stats[table] = 0
        
        return stats


# Global database instance (initialized by startup.py)
_db: Optional[Database] = None


def init_database(db_path: Path, logger: Optional[logging.Logger] = None) -> Database:
    """
    Initialize the global database instance.
    
    Args:
        db_path: Path to SQLite database file
        logger: Optional logger
        
    Returns:
        Initialized Database instance
    """
    global _db
    _db = Database(db_path, logger)
    _db.initialize()
    return _db


def get_database() -> Database:
    """
    Get the global database instance.
    
    Returns:
        Database instance
        
    Raises:
        DatabaseError: If database not initialized
    """
    if _db is None:
        raise DatabaseError(
            "Database not initialized. Call init_database() first."
        )
    return _db
