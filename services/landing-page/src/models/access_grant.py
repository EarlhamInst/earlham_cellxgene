"""
Access Grant Model

Represents email-verified access to private datasets.

Constitutional Alignment:
- Principle II (Modular Architecture): Clear data model boundaries
- Principle IV (Fail-Fast): Validates grants on creation
"""

import secrets
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
from pathlib import Path


def generate_access_code() -> str:
    """Generate a 6-digit numeric access code."""
    return f"{secrets.randbelow(1000000):06d}"


def hash_code(code: str) -> str:
    """Hash an access code for storage."""
    return hashlib.sha256(code.encode()).hexdigest()


@dataclass
class AccessGrant:
    """
    Represents access granted to an email for a private dataset.
    
    Attributes:
        id: Unique grant identifier
        dataset_id: ID of the private dataset
        email: Email address granted access
        code_hash: SHA-256 hash of the access code
        created_at: When the grant was created
        expires_at: When the grant expires
        verified: Whether the email has been verified with the code
        verified_at: When verification occurred
        access_log: List of access timestamps
        revoked: Whether access has been revoked
    """
    
    id: str
    dataset_id: str
    email: str
    code_hash: str
    created_at: str  # ISO format
    expires_at: str  # ISO format
    verified: bool = False
    verified_at: Optional[str] = None
    access_log: List[str] = None  # List of ISO timestamps
    revoked: bool = False
    
    def __post_init__(self):
        if self.access_log is None:
            self.access_log = []
    
    @classmethod
    def create(
        cls,
        dataset_id: str,
        email: str,
        access_code: str,
        expires_in_days: int = 90
    ) -> "AccessGrant":
        """
        Create a new access grant.
        
        Args:
            dataset_id: ID of the private dataset
            email: Reviewer's email address
            access_code: The plain-text access code (will be hashed)
            expires_in_days: How many days until the grant expires
            
        Returns:
            AccessGrant instance
        """
        now = datetime.utcnow()
        
        return cls(
            id=secrets.token_urlsafe(16),
            dataset_id=dataset_id,
            email=email.lower().strip(),
            code_hash=hash_code(access_code),
            created_at=now.isoformat(),
            expires_at=(now + timedelta(days=expires_in_days)).isoformat(),
        )
    
    def verify_code(self, code: str) -> bool:
        """
        Verify an access code against this grant.
        
        Args:
            code: The plain-text code to verify
            
        Returns:
            True if code matches and grant is valid
        """
        if self.revoked:
            return False
        
        if self.is_expired():
            return False
        
        if hash_code(code) == self.code_hash:
            self.verified = True
            self.verified_at = datetime.utcnow().isoformat()
            return True
        
        return False
    
    def is_expired(self) -> bool:
        """Check if grant has expired."""
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.utcnow() > expires
    
    def is_valid(self) -> bool:
        """Check if grant is valid for access."""
        return self.verified and not self.revoked and not self.is_expired()
    
    def log_access(self) -> None:
        """Record an access event."""
        self.access_log.append(datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccessGrant":
        """Create from dictionary."""
        return cls(**data)


class AccessGrantStore:
    """
    Persistent storage for access grants using JSON file.
    
    In production, this could be replaced with a database.
    """
    
    def __init__(self, storage_path: Path):
        """
        Initialize the store.
        
        Args:
            storage_path: Path to the JSON storage file
        """
        self.storage_path = Path(storage_path)
        self._ensure_storage_exists()
    
    def _ensure_storage_exists(self) -> None:
        """Create storage file if it doesn't exist."""
        if not self.storage_path.exists():
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_grants({})
    
    def _load_grants(self) -> Dict[str, Dict]:
        """Load all grants from storage."""
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_grants(self, grants: Dict[str, Dict]) -> None:
        """Save all grants to storage."""
        with open(self.storage_path, 'w') as f:
            json.dump(grants, f, indent=2)
    
    def save(self, grant: AccessGrant) -> None:
        """Save or update a grant."""
        grants = self._load_grants()
        grants[grant.id] = grant.to_dict()
        self._save_grants(grants)
    
    def get_by_id(self, grant_id: str) -> Optional[AccessGrant]:
        """Get a grant by ID."""
        grants = self._load_grants()
        if grant_id in grants:
            return AccessGrant.from_dict(grants[grant_id])
        return None
    
    def get_by_email_and_dataset(self, email: str, dataset_id: str) -> Optional[AccessGrant]:
        """Get grant for a specific email and dataset."""
        email = email.lower().strip()
        grants = self._load_grants()
        
        for grant_data in grants.values():
            if grant_data['email'] == email and grant_data['dataset_id'] == dataset_id:
                return AccessGrant.from_dict(grant_data)
        
        return None
    
    def get_grants_for_email(self, email: str) -> List[AccessGrant]:
        """Get all valid grants for an email."""
        email = email.lower().strip()
        grants = self._load_grants()
        
        result = []
        for grant_data in grants.values():
            if grant_data['email'] == email:
                grant = AccessGrant.from_dict(grant_data)
                if grant.is_valid():
                    result.append(grant)
        
        return result
    
    def get_by_email_and_code(self, email: str, code: str) -> Optional[AccessGrant]:
        """Find a grant matching email and code (verifies the code)."""
        email = email.lower().strip()
        code_hashed = hash_code(code)
        grants = self._load_grants()
        
        for grant_data in grants.values():
            if grant_data['email'] == email and grant_data['code_hash'] == code_hashed:
                grant = AccessGrant.from_dict(grant_data)
                if not grant.revoked and not grant.is_expired():
                    return grant
        
        return None
    
    def get_all_grants_for_email(self, email: str) -> List[AccessGrant]:
        """Get all non-revoked, non-expired grants for an email (verified or not)."""
        email = email.lower().strip()
        grants = self._load_grants()
        
        result = []
        for grant_data in grants.values():
            if grant_data['email'] == email:
                grant = AccessGrant.from_dict(grant_data)
                if not grant.revoked and not grant.is_expired():
                    result.append(grant)
        
        return result
    
    def get_grants_for_dataset(self, dataset_id: str) -> List[AccessGrant]:
        """Get all grants for a dataset."""
        grants = self._load_grants()
        
        result = []
        for grant_data in grants.values():
            if grant_data['dataset_id'] == dataset_id:
                result.append(AccessGrant.from_dict(grant_data))
        
        return result
    
    def revoke(self, grant_id: str) -> bool:
        """Revoke a grant by ID."""
        grant = self.get_by_id(grant_id)
        if grant:
            grant.revoked = True
            self.save(grant)
            return True
        return False
    
    def revoke_by_email(self, email: str, dataset_id: str) -> bool:
        """Revoke grant for an email and dataset."""
        grant = self.get_by_email_and_dataset(email, dataset_id)
        if grant:
            grant.revoked = True
            self.save(grant)
            return True
        return False
    
    def cleanup_expired(self) -> int:
        """Remove expired grants. Returns count removed."""
        grants = self._load_grants()
        initial_count = len(grants)
        
        grants = {
            gid: gdata for gid, gdata in grants.items()
            if not AccessGrant.from_dict(gdata).is_expired()
        }
        
        self._save_grants(grants)
        return initial_count - len(grants)
