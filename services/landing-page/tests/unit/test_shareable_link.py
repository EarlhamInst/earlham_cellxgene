"""
Unit tests for ShareableLink model

Tests the ShareableLink data model and store including:
- Link creation and token hashing
- Token verification
- Usage tracking
- Expiration and revocation
- Store persistence

Constitutional Alignment:
- Principle I (Unit Testing): Comprehensive test coverage
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import json
import os

from src.models.shareable_link import (
    ShareableLink,
    ShareableLinkStore,
    generate_share_token,
    hash_token
)


class TestShareableLink:
    """Test suite for ShareableLink model."""
    
    def test_generate_share_token(self):
        """Test that generated tokens are unique and URL-safe."""
        tokens = [generate_share_token() for _ in range(100)]
        
        # All tokens should be unique
        assert len(set(tokens)) == 100
        
        # Tokens should be URL-safe (no special characters that need encoding)
        for token in tokens:
            assert all(c.isalnum() or c in '-_' for c in token)
            # Should be reasonably long (32 bytes = ~43 chars in base64)
            assert len(token) >= 40
    
    def test_hash_token(self):
        """Test token hashing is consistent and one-way."""
        token = "test_token_12345"
        
        # Same input should produce same hash
        hash1 = hash_token(token)
        hash2 = hash_token(token)
        assert hash1 == hash2
        
        # Hash should be 64 chars (SHA-256 hex)
        assert len(hash1) == 64
        
        # Different tokens produce different hashes
        assert hash_token("different_token") != hash1
    
    def test_link_creation(self):
        """Test basic link creation."""
        token = generate_share_token()
        link = ShareableLink.create(
            dataset_id="dataset_123",
            token=token,
            created_by_email="researcher@example.com",
            label="For reviewers",
            expires_in_days=30,
            max_uses=10
        )
        
        assert link.dataset_id == "dataset_123"
        assert link.created_by_email == "researcher@example.com"
        assert link.label == "For reviewers"
        assert link.max_uses == 10
        assert link.use_count == 0
        assert link.revoked is False
        assert link.access_log == []
        assert link.token_hash == hash_token(token)
        
        # Check expiration is in the future
        expires = datetime.fromisoformat(link.expires_at)
        assert expires > datetime.utcnow()
        assert expires < datetime.utcnow() + timedelta(days=31)
    
    def test_link_creation_unlimited_uses(self):
        """Test link creation with unlimited uses."""
        token = generate_share_token()
        link = ShareableLink.create(
            dataset_id="dataset_123",
            token=token,
            created_by_email="admin@example.com",
            max_uses=None  # Unlimited
        )
        
        assert link.max_uses is None
        assert link.is_valid() is True
    
    def test_verify_token_success(self):
        """Test successful token verification."""
        token = generate_share_token()
        link = ShareableLink.create(
            dataset_id="dataset_123",
            token=token,
            created_by_email="test@example.com"
        )
        
        assert link.verify_token(token) is True
    
    def test_verify_token_wrong_token(self):
        """Test verification with wrong token."""
        token = generate_share_token()
        link = ShareableLink.create(
            dataset_id="dataset_123",
            token=token,
            created_by_email="test@example.com"
        )
        
        assert link.verify_token("wrong_token") is False
    
    def test_verify_token_revoked(self):
        """Test verification fails when link is revoked."""
        token = generate_share_token()
        link = ShareableLink.create(
            dataset_id="dataset_123",
            token=token,
            created_by_email="test@example.com"
        )
        
        link.revoked = True
        assert link.verify_token(token) is False
    
    def test_verify_token_expired(self):
        """Test verification fails when link is expired."""
        token = generate_share_token()
        link = ShareableLink.create(
            dataset_id="dataset_123",
            token=token,
            created_by_email="test@example.com",
            expires_in_days=-1  # Already expired
        )
        
        assert link.verify_token(token) is False
    
    def test_verify_token_max_uses_reached(self):
        """Test verification fails when max uses reached."""
        token = generate_share_token()
        link = ShareableLink.create(
            dataset_id="dataset_123",
            token=token,
            created_by_email="test@example.com",
            max_uses=2
        )
        
        # Use up the link
        link.use_count = 2
        assert link.verify_token(token) is False
    
    def test_is_expired(self):
        """Test expiration checking."""
        token = generate_share_token()
        
        # Not expired
        link_valid = ShareableLink.create(
            dataset_id="dataset_123",
            token=token,
            created_by_email="test@example.com",
            expires_in_days=30
        )
        assert link_valid.is_expired() is False
        
        # Expired
        link_expired = ShareableLink.create(
            dataset_id="dataset_123",
            token=token,
            created_by_email="test@example.com",
            expires_in_days=-1
        )
        assert link_expired.is_expired() is True
    
    def test_is_valid(self):
        """Test comprehensive validity checking."""
        token = generate_share_token()
        link = ShareableLink.create(
            dataset_id="dataset_123",
            token=token,
            created_by_email="test@example.com",
            max_uses=5
        )
        
        # Initially valid
        assert link.is_valid() is True
        
        # Revoked -> invalid
        link.revoked = True
        assert link.is_valid() is False
        link.revoked = False
        
        # Max uses reached -> invalid
        link.use_count = 5
        assert link.is_valid() is False
    
    def test_record_use(self):
        """Test usage recording."""
        token = generate_share_token()
        link = ShareableLink.create(
            dataset_id="dataset_123",
            token=token,
            created_by_email="test@example.com"
        )
        
        assert link.use_count == 0
        assert link.last_used_at is None
        assert len(link.access_log) == 0
        
        # Record first use
        link.record_use(ip_address="192.168.1.1", user_agent="Mozilla/5.0")
        
        assert link.use_count == 1
        assert link.last_used_at is not None
        assert len(link.access_log) == 1
        assert link.access_log[0]["ip"] == "192.168.1.1"
        assert "Mozilla" in link.access_log[0]["user_agent"]
        
        # Record second use
        link.record_use(ip_address="10.0.0.1")
        
        assert link.use_count == 2
        assert len(link.access_log) == 2
    
    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization."""
        token = generate_share_token()
        link = ShareableLink.create(
            dataset_id="dataset_123",
            token=token,
            created_by_email="test@example.com",
            label="Test label",
            max_uses=10
        )
        
        # Add some usage
        link.record_use(ip_address="192.168.1.1")
        
        # Round-trip
        data = link.to_dict()
        restored = ShareableLink.from_dict(data)
        
        assert restored.id == link.id
        assert restored.dataset_id == link.dataset_id
        assert restored.token_hash == link.token_hash
        assert restored.label == link.label
        assert restored.use_count == link.use_count
        assert len(restored.access_log) == len(link.access_log)
    
    def test_to_public_dict(self):
        """Test public dict excludes sensitive data."""
        token = generate_share_token()
        link = ShareableLink.create(
            dataset_id="dataset_123",
            token=token,
            created_by_email="test@example.com"
        )
        
        public = link.to_public_dict()
        
        # Should NOT include token_hash or created_by_email
        assert "token_hash" not in public
        assert "created_by_email" not in public
        
        # Should include basic info
        assert public["id"] == link.id
        assert public["dataset_id"] == link.dataset_id
        assert "is_valid" in public


class TestShareableLinkStore:
    """Test suite for ShareableLinkStore."""
    
    @pytest.fixture
    def temp_store(self):
        """Create a temporary store for testing."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        
        store = ShareableLinkStore(temp_path)
        yield store
        
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()
    
    def test_store_creation(self, temp_store):
        """Test store creates storage file."""
        assert temp_store.storage_path.exists()
    
    def test_save_and_get_by_id(self, temp_store):
        """Test saving and retrieving by ID."""
        token = generate_share_token()
        link = ShareableLink.create(
            dataset_id="dataset_123",
            token=token,
            created_by_email="test@example.com"
        )
        
        temp_store.save(link)
        
        retrieved = temp_store.get_by_id(link.id)
        assert retrieved is not None
        assert retrieved.id == link.id
        assert retrieved.dataset_id == link.dataset_id
    
    def test_get_by_id_not_found(self, temp_store):
        """Test get_by_id returns None for unknown ID."""
        result = temp_store.get_by_id("nonexistent_id")
        assert result is None
    
    def test_get_by_token(self, temp_store):
        """Test retrieving by token."""
        token = generate_share_token()
        link = ShareableLink.create(
            dataset_id="dataset_123",
            token=token,
            created_by_email="test@example.com"
        )
        
        temp_store.save(link)
        
        retrieved = temp_store.get_by_token(token)
        assert retrieved is not None
        assert retrieved.id == link.id
    
    def test_get_by_token_expired_not_returned(self, temp_store):
        """Test expired links not returned by get_by_token."""
        token = generate_share_token()
        link = ShareableLink.create(
            dataset_id="dataset_123",
            token=token,
            created_by_email="test@example.com",
            expires_in_days=-1  # Already expired
        )
        
        temp_store.save(link)
        
        retrieved = temp_store.get_by_token(token)
        assert retrieved is None
    
    def test_get_by_token_revoked_not_returned(self, temp_store):
        """Test revoked links not returned by get_by_token."""
        token = generate_share_token()
        link = ShareableLink.create(
            dataset_id="dataset_123",
            token=token,
            created_by_email="test@example.com"
        )
        link.revoked = True
        
        temp_store.save(link)
        
        retrieved = temp_store.get_by_token(token)
        assert retrieved is None
    
    def test_get_links_for_dataset(self, temp_store):
        """Test getting all links for a dataset."""
        # Create multiple links for same dataset
        for i in range(3):
            token = generate_share_token()
            link = ShareableLink.create(
                dataset_id="dataset_A",
                token=token,
                created_by_email=f"user{i}@example.com"
            )
            temp_store.save(link)
        
        # Create link for different dataset
        token = generate_share_token()
        link_b = ShareableLink.create(
            dataset_id="dataset_B",
            token=token,
            created_by_email="other@example.com"
        )
        temp_store.save(link_b)
        
        # Get links for dataset_A
        links = temp_store.get_links_for_dataset("dataset_A")
        assert len(links) == 3
        assert all(l.dataset_id == "dataset_A" for l in links)
    
    def test_get_links_by_creator(self, temp_store):
        """Test getting all links created by an email."""
        # Create links from same creator
        for i in range(2):
            token = generate_share_token()
            link = ShareableLink.create(
                dataset_id=f"dataset_{i}",
                token=token,
                created_by_email="creator@example.com"
            )
            temp_store.save(link)
        
        # Create link from different creator
        token = generate_share_token()
        other_link = ShareableLink.create(
            dataset_id="dataset_other",
            token=token,
            created_by_email="other@example.com"
        )
        temp_store.save(other_link)
        
        # Get links by creator
        links = temp_store.get_links_by_creator("creator@example.com")
        assert len(links) == 2
        
        # Email should be case-insensitive
        links_upper = temp_store.get_links_by_creator("CREATOR@example.com")
        assert len(links_upper) == 2
    
    def test_revoke(self, temp_store):
        """Test revoking a link."""
        token = generate_share_token()
        link = ShareableLink.create(
            dataset_id="dataset_123",
            token=token,
            created_by_email="test@example.com"
        )
        temp_store.save(link)
        
        # Revoke
        result = temp_store.revoke(link.id)
        assert result is True
        
        # Verify revoked
        retrieved = temp_store.get_by_id(link.id)
        assert retrieved.revoked is True
        
        # Token should no longer work
        token_result = temp_store.get_by_token(token)
        assert token_result is None
    
    def test_revoke_nonexistent(self, temp_store):
        """Test revoking nonexistent link returns False."""
        result = temp_store.revoke("nonexistent_id")
        assert result is False
    
    def test_revoke_all_for_dataset(self, temp_store):
        """Test revoking all links for a dataset."""
        # Create multiple links for same dataset
        for i in range(3):
            token = generate_share_token()
            link = ShareableLink.create(
                dataset_id="dataset_to_revoke",
                token=token,
                created_by_email=f"user{i}@example.com"
            )
            temp_store.save(link)
        
        # Create link for different dataset
        token = generate_share_token()
        link_other = ShareableLink.create(
            dataset_id="other_dataset",
            token=token,
            created_by_email="other@example.com"
        )
        temp_store.save(link_other)
        
        # Revoke all for dataset
        count = temp_store.revoke_all_for_dataset("dataset_to_revoke")
        assert count == 3
        
        # Verify all revoked
        links = temp_store.get_links_for_dataset("dataset_to_revoke")
        assert all(l.revoked for l in links)
        
        # Other dataset unaffected
        other_retrieved = temp_store.get_by_id(link_other.id)
        assert other_retrieved.revoked is False
    
    def test_cleanup_expired(self, temp_store):
        """Test cleaning up expired links."""
        # Create expired links
        for i in range(2):
            token = generate_share_token()
            link = ShareableLink.create(
                dataset_id=f"expired_{i}",
                token=token,
                created_by_email="test@example.com",
                expires_in_days=-1
            )
            temp_store.save(link)
        
        # Create valid link
        token = generate_share_token()
        valid_link = ShareableLink.create(
            dataset_id="valid_dataset",
            token=token,
            created_by_email="test@example.com",
            expires_in_days=30
        )
        temp_store.save(valid_link)
        
        # Cleanup
        removed = temp_store.cleanup_expired()
        assert removed == 2
        
        # Valid link should still exist
        retrieved = temp_store.get_by_id(valid_link.id)
        assert retrieved is not None
    
    def test_get_stats(self, temp_store):
        """Test getting statistics."""
        # Create various links
        # Active
        token = generate_share_token()
        active = ShareableLink.create(
            dataset_id="ds1", token=token, created_by_email="test@example.com"
        )
        temp_store.save(active)
        
        # Revoked
        token = generate_share_token()
        revoked = ShareableLink.create(
            dataset_id="ds2", token=token, created_by_email="test@example.com"
        )
        revoked.revoked = True
        temp_store.save(revoked)
        
        # Expired
        token = generate_share_token()
        expired = ShareableLink.create(
            dataset_id="ds3", token=token, created_by_email="test@example.com",
            expires_in_days=-1
        )
        temp_store.save(expired)
        
        # Exhausted (max uses reached)
        token = generate_share_token()
        exhausted = ShareableLink.create(
            dataset_id="ds4", token=token, created_by_email="test@example.com",
            max_uses=1
        )
        exhausted.use_count = 1
        temp_store.save(exhausted)
        
        stats = temp_store.get_stats()
        
        assert stats["total"] == 4
        assert stats["active"] == 1
        assert stats["revoked"] == 1
        assert stats["expired"] == 1
        assert stats["exhausted"] == 1
