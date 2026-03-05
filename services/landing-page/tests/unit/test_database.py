"""
Unit tests for SQLite Database Service

Tests the database module including:
- Database initialization and schema creation
- Connection management
- Transaction handling
- Schema versioning

Constitutional Alignment:
- Principle I (Unit Testing): Comprehensive test coverage
"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime

from src.services.database import (
    Database, 
    init_database, 
    get_database, 
    DatabaseError,
    CURRENT_SCHEMA_VERSION
)


class TestDatabase:
    """Test suite for Database class."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        os.unlink(path)  # Remove so database can create it
        yield Path(path)
        # Cleanup
        if Path(path).exists():
            os.unlink(path)
    
    @pytest.fixture
    def database(self, temp_db_path):
        """Create a database instance for testing."""
        db = Database(temp_db_path)
        db.initialize()
        return db
    
    def test_database_initialization_creates_file(self, temp_db_path):
        """Test that database initialization creates the file."""
        assert not temp_db_path.exists()
        
        db = Database(temp_db_path)
        db.initialize()
        
        assert temp_db_path.exists()
    
    def test_database_creates_all_tables(self, database):
        """Test that all required tables are created."""
        expected_tables = [
            'users',
            'datasets',
            'access_grants',
            'access_grant_log',
            'shareable_links',
            'shareable_link_log',
            'schema_version'
        ]
        
        for table in expected_tables:
            assert database.table_exists(table), f"Table {table} should exist"
    
    def test_schema_version_is_set(self, database):
        """Test that schema version is properly set."""
        row = database.execute_one(
            "SELECT MAX(version) as version FROM schema_version"
        )
        assert row['version'] == CURRENT_SCHEMA_VERSION
    
    def test_database_initialization_is_idempotent(self, temp_db_path):
        """Test that initializing twice doesn't cause errors."""
        db = Database(temp_db_path)
        db.initialize()
        db.initialize()  # Should not raise
        
        # Verify schema version wasn't doubled
        rows = db.execute("SELECT * FROM schema_version")
        assert len(rows) == 1
    
    def test_get_connection_returns_valid_connection(self, database):
        """Test getting a database connection."""
        with database.get_connection() as conn:
            cursor = conn.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
    
    def test_connection_has_row_factory(self, database):
        """Test that connections use Row factory."""
        with database.get_connection() as conn:
            conn.execute(
                "INSERT INTO users (orcid_id, display_name, created_at, last_login_at) VALUES (?, ?, ?, ?)",
                ("0000-0001-2345-6789", "Test User", datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
            )
            conn.commit()
            
            cursor = conn.execute("SELECT * FROM users WHERE orcid_id = ?", ("0000-0001-2345-6789",))
            row = cursor.fetchone()
            
            # Should be able to access by column name
            assert row['display_name'] == "Test User"
    
    def test_transaction_commits_on_success(self, database):
        """Test that transactions commit on successful completion."""
        with database.transaction() as conn:
            conn.execute(
                "INSERT INTO users (orcid_id, display_name, created_at, last_login_at) VALUES (?, ?, ?, ?)",
                ("0000-0001-2345-6789", "Test User", datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
            )
        
        # Verify data persisted
        row = database.execute_one("SELECT * FROM users WHERE orcid_id = ?", ("0000-0001-2345-6789",))
        assert row is not None
    
    def test_transaction_rolls_back_on_error(self, database):
        """Test that transactions roll back on error."""
        try:
            with database.transaction() as conn:
                conn.execute(
                    "INSERT INTO users (orcid_id, display_name, created_at, last_login_at) VALUES (?, ?, ?, ?)",
                    ("0000-0001-2345-6789", "Test User", datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
                )
                raise ValueError("Simulated error")
        except ValueError:
            pass
        
        # Verify data was rolled back
        row = database.execute_one("SELECT * FROM users WHERE orcid_id = ?", ("0000-0001-2345-6789",))
        assert row is None
    
    def test_execute_returns_all_results(self, database):
        """Test execute method returns all matching rows."""
        now = datetime.utcnow().isoformat()
        
        with database.transaction() as conn:
            conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", 
                        ("0000-0001", "User 1", None, now, now, 50*1024**3, 0))
            conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", 
                        ("0000-0002", "User 2", None, now, now, 50*1024**3, 0))
            conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", 
                        ("0000-0003", "User 3", None, now, now, 50*1024**3, 0))
        
        rows = database.execute("SELECT * FROM users")
        assert len(rows) == 3
    
    def test_execute_one_returns_single_result(self, database):
        """Test execute_one method returns single row."""
        now = datetime.utcnow().isoformat()
        
        with database.transaction() as conn:
            conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", 
                        ("0000-0001", "User 1", None, now, now, 50*1024**3, 0))
        
        row = database.execute_one("SELECT * FROM users WHERE orcid_id = ?", ("0000-0001",))
        assert row['display_name'] == "User 1"
    
    def test_execute_one_returns_none_for_no_match(self, database):
        """Test execute_one returns None when no match."""
        row = database.execute_one("SELECT * FROM users WHERE orcid_id = ?", ("nonexistent",))
        assert row is None
    
    def test_execute_write_returns_affected_count(self, database):
        """Test execute_write returns number of affected rows."""
        now = datetime.utcnow().isoformat()
        
        with database.transaction() as conn:
            conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", 
                        ("0000-0001", "User 1", None, now, now, 50*1024**3, 0))
            conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", 
                        ("0000-0002", "User 2", None, now, now, 50*1024**3, 0))
        
        affected = database.execute_write(
            "UPDATE users SET display_name = ?", ("Updated",)
        )
        assert affected == 2
    
    def test_get_table_info(self, database):
        """Test getting table column information."""
        info = database.get_table_info("users")
        
        column_names = {col['name'] for col in info}
        assert 'orcid_id' in column_names
        assert 'display_name' in column_names
        assert 'email' in column_names
    
    def test_get_stats(self, database):
        """Test getting database statistics."""
        stats = database.get_stats()
        
        assert 'users' in stats
        assert 'datasets' in stats
        assert 'access_grants' in stats
        assert 'shareable_links' in stats
        
        # All should be 0 initially
        for count in stats.values():
            assert count == 0
    
    def test_foreign_keys_enabled(self, database):
        """Test that foreign keys are enforced."""
        now = datetime.utcnow().isoformat()
        
        # Try to insert a dataset with non-existent owner
        # This should fail because foreign keys are enabled
        with pytest.raises(Exception):
            with database.transaction() as conn:
                conn.execute("""
                    INSERT INTO datasets 
                    (id, filename, filepath, display_name, organism, tissue, assay, 
                     owner_orcid, visibility, source, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "test", "test.h5ad", "/path/test.h5ad", "Test", 
                    "Human", "Blood", "10x",
                    "nonexistent-orcid",  # This should fail FK constraint
                    "public", "user_upload", now, now
                ))


class TestGlobalDatabaseFunctions:
    """Test global database initialization functions."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        os.unlink(path)
        yield Path(path)
        if Path(path).exists():
            os.unlink(path)
    
    def test_init_database_returns_database(self, temp_db_path):
        """Test init_database returns a Database instance."""
        db = init_database(temp_db_path)
        assert isinstance(db, Database)
    
    def test_get_database_raises_when_not_initialized(self):
        """Test get_database raises error when not initialized."""
        # Reset global state
        import src.services.database as db_module
        db_module._db = None
        
        with pytest.raises(DatabaseError):
            get_database()
    
    def test_get_database_returns_initialized_db(self, temp_db_path):
        """Test get_database returns the initialized database."""
        db1 = init_database(temp_db_path)
        db2 = get_database()
        
        assert db1 is db2
