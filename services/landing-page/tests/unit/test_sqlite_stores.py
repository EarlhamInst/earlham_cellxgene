"""
Unit tests for SQLite-backed stores

Tests the SQLite implementations of:
- AccessGrantStoreSQLite
- ShareableLinkStoreSQLite
- DatasetStoreSQLite

Constitutional Alignment:
- Principle I (Unit Testing): Comprehensive test coverage
"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta

from src.services.database import Database
from src.models.access_grant import (
    AccessGrant, 
    AccessGrantStoreSQLite, 
    generate_access_code,
    hash_code
)
from src.models.shareable_link import (
    ShareableLink,
    ShareableLinkStoreSQLite,
    generate_share_token,
    hash_token
)
from src.models.dataset import (
    Dataset,
    DatasetStoreSQLite,
    VISIBILITY_PUBLIC,
    VISIBILITY_UNLISTED,
    VISIBILITY_PRIVATE,
    SOURCE_CURATED,
    SOURCE_USER_UPLOAD
)


def create_test_dataset(database, dataset_id: str = "test-dataset") -> Dataset:
    """
    Helper function to create a test dataset in the database.
    
    This is needed because access_grants and shareable_links have
    foreign key constraints referencing the datasets table.
    """
    dataset_store = DatasetStoreSQLite(database)
    
    # Check if dataset already exists
    existing = dataset_store.get_by_id(dataset_id)
    if existing:
        return existing
    
    dataset = Dataset(
        id=dataset_id,
        filename=f"{dataset_id}.h5ad",
        filepath=Path(f"/data/{dataset_id}.h5ad"),
        display_name=f"Test Dataset {dataset_id}",
        description="Test dataset for unit tests",
        organism="Test Organism",
        tissue="Test Tissue",
        assay="Test Assay",
        cell_count=1000,
        gene_count=500,
    )
    dataset_store.save(dataset)
    return dataset


class TestAccessGrantStoreSQLite:
    """Test suite for AccessGrantStoreSQLite."""
    
    @pytest.fixture
    def database(self):
        """Create an in-memory database for testing."""
        db = Database(":memory:")
        db.initialize()
        return db
    
    @pytest.fixture
    def test_dataset(self, database):
        """Create a test dataset for foreign key references."""
        return create_test_dataset(database, "test-dataset")
    
    @pytest.fixture
    def store(self, database):
        """Create an AccessGrantStoreSQLite instance."""
        return AccessGrantStoreSQLite(database)
    
    @pytest.fixture
    def sample_grant(self, test_dataset):
        """Create a sample access grant."""
        code = generate_access_code()
        return AccessGrant.create(
            dataset_id=test_dataset.id,
            email="test@example.com",
            access_code=code,
            expires_in_days=30
        ), code
    
    def test_save_and_get_by_id(self, store, sample_grant):
        """Test saving and retrieving a grant by ID."""
        grant, _ = sample_grant
        
        store.save(grant)
        retrieved = store.get_by_id(grant.id)
        
        assert retrieved is not None
        assert retrieved.id == grant.id
        assert retrieved.dataset_id == grant.dataset_id
        assert retrieved.email == grant.email
    
    def test_get_by_id_returns_none_for_missing(self, store):
        """Test get_by_id returns None for non-existent ID."""
        result = store.get_by_id("nonexistent")
        assert result is None
    
    def test_get_by_email_and_dataset(self, store, sample_grant):
        """Test finding grant by email and dataset."""
        grant, _ = sample_grant
        store.save(grant)
        
        retrieved = store.get_by_email_and_dataset("test@example.com", "test-dataset")
        
        assert retrieved is not None
        assert retrieved.id == grant.id
    
    def test_get_by_email_and_dataset_case_insensitive(self, store, sample_grant):
        """Test email lookup is case-insensitive."""
        grant, _ = sample_grant
        store.save(grant)
        
        retrieved = store.get_by_email_and_dataset("TEST@EXAMPLE.COM", "test-dataset")
        
        assert retrieved is not None
    
    def test_get_grants_for_email(self, store, database):
        """Test getting all valid grants for an email."""
        # Create datasets for foreign key constraints
        for i in range(3):
            create_test_dataset(database, f"dataset-{i}")
        
        # Create and save multiple grants
        for i in range(3):
            code = generate_access_code()
            grant = AccessGrant.create(
                dataset_id=f"dataset-{i}",
                email="user@example.com",
                access_code=code
            )
            grant.verified = True
            store.save(grant)
        
        grants = store.get_grants_for_email("user@example.com")
        assert len(grants) == 3
    
    def test_get_grants_for_email_excludes_unverified(self, store, test_dataset):
        """Test that unverified grants are excluded."""
        code = generate_access_code()
        grant = AccessGrant.create(
            dataset_id=test_dataset.id,
            email="user@example.com",
            access_code=code
        )
        grant.verified = False  # Not verified
        store.save(grant)
        
        grants = store.get_grants_for_email("user@example.com")
        assert len(grants) == 0
    
    def test_get_by_email_and_code(self, store, sample_grant):
        """Test finding grant by email and code."""
        grant, code = sample_grant
        store.save(grant)
        
        retrieved = store.get_by_email_and_code("test@example.com", code)
        
        assert retrieved is not None
        assert retrieved.id == grant.id
    
    def test_get_by_email_and_code_wrong_code(self, store, sample_grant):
        """Test wrong code returns None."""
        grant, _ = sample_grant
        store.save(grant)
        
        retrieved = store.get_by_email_and_code("test@example.com", "000000")
        assert retrieved is None
    
    def test_revoke(self, store, sample_grant):
        """Test revoking a grant."""
        grant, _ = sample_grant
        store.save(grant)
        
        result = store.revoke(grant.id)
        
        assert result is True
        retrieved = store.get_by_id(grant.id)
        assert retrieved.revoked is True
    
    def test_revoke_nonexistent_returns_false(self, store):
        """Test revoking non-existent grant returns False."""
        result = store.revoke("nonexistent")
        assert result is False
    
    def test_log_access(self, store, database, sample_grant):
        """Test logging access events."""
        grant, _ = sample_grant
        store.save(grant)
        
        store.log_access(grant.id, ip_address="192.168.1.1", user_agent="TestAgent")
        
        # Verify log was recorded
        logs = database.execute(
            "SELECT * FROM access_grant_log WHERE grant_id = ?",
            (grant.id,)
        )
        assert len(logs) == 1
        assert logs[0]['ip_address'] == "192.168.1.1"
    
    def test_cleanup_expired(self, store, database):
        """Test cleaning up expired grants."""
        # Create test dataset for foreign key constraint
        test_ds = create_test_dataset(database, "test")
        
        # Create an expired grant
        now = datetime.utcnow()
        expired_grant = AccessGrant(
            id="expired",
            dataset_id="test",
            email="test@example.com",
            code_hash=hash_code("123456"),
            created_at=(now - timedelta(days=100)).isoformat(),
            expires_at=(now - timedelta(days=10)).isoformat()  # Expired
        )
        store.save(expired_grant)
        
        # Create a valid grant
        valid_grant = AccessGrant(
            id="valid",
            dataset_id="test",
            email="test@example.com",
            code_hash=hash_code("123456"),
            created_at=now.isoformat(),
            expires_at=(now + timedelta(days=30)).isoformat()  # Not expired
        )
        store.save(valid_grant)
        
        removed = store.cleanup_expired()
        
        assert removed == 1
        assert store.get_by_id("expired") is None
        assert store.get_by_id("valid") is not None


class TestShareableLinkStoreSQLite:
    """Test suite for ShareableLinkStoreSQLite."""
    
    @pytest.fixture
    def database(self):
        """Create an in-memory database for testing."""
        db = Database(":memory:")
        db.initialize()
        return db
    
    @pytest.fixture
    def test_dataset(self, database):
        """Create a test dataset for foreign key references."""
        return create_test_dataset(database, "test-dataset")
    
    @pytest.fixture
    def store(self, database):
        """Create a ShareableLinkStoreSQLite instance."""
        return ShareableLinkStoreSQLite(database)
    
    @pytest.fixture
    def sample_link(self, test_dataset):
        """Create a sample shareable link."""
        token = generate_share_token()
        return ShareableLink.create(
            dataset_id=test_dataset.id,
            token=token,
            created_by_email="creator@example.com",
            label="Test Link",
            expires_in_days=30
        ), token
    
    def test_save_and_get_by_id(self, store, sample_link):
        """Test saving and retrieving a link by ID."""
        link, _ = sample_link
        
        store.save(link)
        retrieved = store.get_by_id(link.id)
        
        assert retrieved is not None
        assert retrieved.id == link.id
        assert retrieved.dataset_id == link.dataset_id
        assert retrieved.label == link.label
    
    def test_get_by_token(self, store, sample_link):
        """Test finding link by token."""
        link, token = sample_link
        store.save(link)
        
        retrieved = store.get_by_token(token)
        
        assert retrieved is not None
        assert retrieved.id == link.id
    
    def test_get_by_token_excludes_revoked(self, store, sample_link):
        """Test revoked links not returned by get_by_token."""
        link, token = sample_link
        link.revoked = True
        store.save(link)
        
        retrieved = store.get_by_token(token)
        assert retrieved is None
    
    def test_get_by_token_excludes_exhausted(self, store, sample_link):
        """Test exhausted links not returned by get_by_token."""
        link, token = sample_link
        link.max_uses = 5
        link.use_count = 5  # Exhausted
        store.save(link)
        
        retrieved = store.get_by_token(token)
        assert retrieved is None
    
    def test_get_links_for_dataset(self, store, database):
        """Test getting all links for a dataset."""
        # Create test dataset for foreign key constraint
        create_test_dataset(database, "shared-dataset")
        
        for i in range(3):
            token = generate_share_token()
            link = ShareableLink.create(
                dataset_id="shared-dataset",
                token=token,
                created_by_email="creator@example.com"
            )
            store.save(link)
        
        links = store.get_links_for_dataset("shared-dataset")
        assert len(links) == 3
    
    def test_get_links_by_creator(self, store, database):
        """Test getting links by creator email."""
        # Create test datasets for foreign key constraints
        for i in range(2):
            create_test_dataset(database, f"dataset-{i}")
        
        for i in range(2):
            token = generate_share_token()
            link = ShareableLink.create(
                dataset_id=f"dataset-{i}",
                token=token,
                created_by_email="creator@example.com"
            )
            store.save(link)
        
        links = store.get_links_by_creator("creator@example.com")
        assert len(links) == 2
    
    def test_revoke(self, store, sample_link):
        """Test revoking a link."""
        link, _ = sample_link
        store.save(link)
        
        result = store.revoke(link.id)
        
        assert result is True
        retrieved = store.get_by_id(link.id)
        assert retrieved.revoked is True
    
    def test_revoke_all_for_dataset(self, store, database):
        """Test revoking all links for a dataset."""
        # Create test dataset for foreign key constraint
        create_test_dataset(database, "dataset-to-revoke")
        
        for i in range(3):
            token = generate_share_token()
            link = ShareableLink.create(
                dataset_id="dataset-to-revoke",
                token=token,
                created_by_email="creator@example.com"
            )
            store.save(link)
        
        count = store.revoke_all_for_dataset("dataset-to-revoke")
        
        assert count == 3
        links = store.get_links_for_dataset("dataset-to-revoke")
        assert all(link.revoked for link in links)
    
    def test_log_access(self, store, database, sample_link):
        """Test logging access and incrementing use count."""
        link, token = sample_link
        store.save(link)
        
        store.log_access(link.id, ip_address="192.168.1.1", user_agent="TestAgent")
        
        # Verify use_count incremented
        retrieved = store.get_by_id(link.id)
        assert retrieved.use_count == 1
        assert retrieved.last_used_at is not None
        
        # Verify log recorded
        logs = database.execute(
            "SELECT * FROM shareable_link_log WHERE link_id = ?",
            (link.id,)
        )
        assert len(logs) == 1
    
    def test_get_stats(self, store, database):
        """Test getting link statistics."""
        # Create test datasets for foreign key constraints
        create_test_dataset(database, "ds1")
        create_test_dataset(database, "ds2")
        
        now = datetime.utcnow()
        
        # Create links with different states
        token1 = generate_share_token()
        active_link = ShareableLink.create("ds1", token1, "a@example.com")
        store.save(active_link)
        
        token2 = generate_share_token()
        revoked_link = ShareableLink.create("ds2", token2, "a@example.com")
        revoked_link.revoked = True
        store.save(revoked_link)
        
        stats = store.get_stats()
        
        assert stats['total'] == 2
        assert stats['active'] == 1
        assert stats['revoked'] == 1


class TestDatasetStoreSQLite:
    """Test suite for DatasetStoreSQLite."""
    
    @pytest.fixture
    def database(self):
        """Create an in-memory database for testing."""
        db = Database(":memory:")
        db.initialize()
        return db
    
    @pytest.fixture
    def store(self, database):
        """Create a DatasetStoreSQLite instance."""
        return DatasetStoreSQLite(database)
    
    @pytest.fixture
    def sample_dataset(self, tmp_path):
        """Create a sample dataset."""
        filepath = tmp_path / "test.h5ad"
        filepath.touch()
        
        return Dataset(
            id="test-dataset",
            filename="test.h5ad",
            filepath=filepath,
            display_name="Test Dataset",
            description="A test dataset",
            organism="Homo sapiens",
            tissue="Blood",
            assay="10x 3' v3",
            cell_count=1000,
            gene_count=20000
        )
    
    def test_save_and_get_by_id(self, store, sample_dataset):
        """Test saving and retrieving a dataset by ID."""
        store.save(sample_dataset)
        
        retrieved = store.get_by_id("test-dataset")
        
        assert retrieved is not None
        assert retrieved.id == sample_dataset.id
        assert retrieved.display_name == sample_dataset.display_name
        assert retrieved.organism == sample_dataset.organism
    
    def test_get_all(self, store, tmp_path):
        """Test getting all datasets."""
        for i in range(3):
            filepath = tmp_path / f"dataset{i}.h5ad"
            filepath.touch()
            dataset = Dataset(
                id=f"dataset-{i}",
                filename=f"dataset{i}.h5ad",
                filepath=filepath,
                display_name=f"Dataset {i}",
                description="Test",
                organism="Human",
                tissue="Tissue",
                assay="Assay"
            )
            store.save(dataset)
        
        all_datasets = store.get_all()
        assert len(all_datasets) == 3
    
    def test_get_public(self, store, tmp_path):
        """Test getting only public datasets."""
        # Create public dataset
        filepath1 = tmp_path / "public.h5ad"
        filepath1.touch()
        public = Dataset(
            id="public",
            filename="public.h5ad",
            filepath=filepath1,
            display_name="Public Dataset",
            description="Test",
            organism="Human",
            tissue="Tissue",
            assay="Assay",
            visibility=VISIBILITY_PUBLIC
        )
        store.save(public)
        
        # Create private dataset
        filepath2 = tmp_path / "private.h5ad"
        filepath2.touch()
        private = Dataset(
            id="private",
            filename="private.h5ad",
            filepath=filepath2,
            display_name="Private Dataset",
            description="Test",
            organism="Human",
            tissue="Tissue",
            assay="Assay",
            visibility=VISIBILITY_PRIVATE
        )
        store.save(private)
        
        public_datasets = store.get_public()
        
        assert len(public_datasets) == 1
        assert public_datasets[0].id == "public"
    
    def test_get_by_owner(self, store, database, tmp_path):
        """Test getting datasets by owner."""
        # Create user first
        now = datetime.utcnow().isoformat()
        with database.transaction() as conn:
            conn.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("0000-0001", "Test User", None, now, now, 50*1024**3, 0)
            )
        
        # Create dataset owned by user
        filepath = tmp_path / "owned.h5ad"
        filepath.touch()
        dataset = Dataset(
            id="owned",
            filename="owned.h5ad",
            filepath=filepath,
            display_name="Owned Dataset",
            description="Test",
            organism="Human",
            tissue="Tissue",
            assay="Assay",
            owner_orcid="0000-0001",
            source=SOURCE_USER_UPLOAD
        )
        store.save(dataset)
        
        owned = store.get_by_owner("0000-0001")
        
        assert len(owned) == 1
        assert owned[0].id == "owned"
    
    def test_delete(self, store, sample_dataset):
        """Test deleting a dataset."""
        store.save(sample_dataset)
        
        result = store.delete("test-dataset")
        
        assert result is True
        assert store.get_by_id("test-dataset") is None
    
    def test_update_visibility(self, store, sample_dataset):
        """Test updating dataset visibility."""
        sample_dataset.visibility = VISIBILITY_PRIVATE
        store.save(sample_dataset)
        
        result = store.update_visibility("test-dataset", VISIBILITY_PUBLIC)
        
        assert result is True
        retrieved = store.get_by_id("test-dataset")
        assert retrieved.visibility == VISIBILITY_PUBLIC
    
    def test_update_visibility_invalid_raises(self, store, sample_dataset):
        """Test invalid visibility raises error."""
        store.save(sample_dataset)
        
        with pytest.raises(ValueError):
            store.update_visibility("test-dataset", "invalid")
    
    def test_increment_view_count(self, store, sample_dataset):
        """Test incrementing view count."""
        store.save(sample_dataset)
        
        store.increment_view_count("test-dataset")
        store.increment_view_count("test-dataset")
        
        retrieved = store.get_by_id("test-dataset")
        assert retrieved.view_count == 2
    
    def test_sync_curated_datasets(self, store, tmp_path):
        """Test syncing curated datasets from filesystem."""
        # Create initial datasets
        datasets = []
        for i in range(3):
            filepath = tmp_path / f"curated{i}.h5ad"
            filepath.touch()
            dataset = Dataset(
                id=f"curated-{i}",
                filename=f"curated{i}.h5ad",
                filepath=filepath,
                display_name=f"Curated {i}",
                description="Test",
                organism="Human",
                tissue="Tissue",
                assay="Assay"
            )
            datasets.append(dataset)
        
        stats = store.sync_curated_datasets(datasets)
        
        assert stats['added'] == 3
        assert stats['updated'] == 0
        assert stats['removed'] == 0
        
        # Sync again with same datasets (should be updates)
        stats = store.sync_curated_datasets(datasets)
        assert stats['added'] == 0
        assert stats['updated'] == 3
        assert stats['removed'] == 0
        
        # Remove one dataset
        stats = store.sync_curated_datasets(datasets[:2])
        assert stats['removed'] == 1
    
    def test_dataset_with_additional_metadata(self, store, tmp_path):
        """Test datasets with additional metadata are preserved."""
        filepath = tmp_path / "meta.h5ad"
        filepath.touch()
        
        dataset = Dataset(
            id="with-meta",
            filename="meta.h5ad",
            filepath=filepath,
            display_name="With Metadata",
            description="Test",
            organism="Human",
            tissue="Tissue",
            assay="Assay",
            additional_metadata={"custom_field": ["value1", "value2"]}
        )
        store.save(dataset)
        
        retrieved = store.get_by_id("with-meta")
        
        assert retrieved.additional_metadata == {"custom_field": ["value1", "value2"]}
