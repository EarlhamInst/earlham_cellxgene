"""
Shareable Link Model

Represents a one-click shareable link for private dataset access.

Constitutional Alignment:
- Principle II (Modular Architecture): Clear data model boundaries
- Principle IV (Fail-Fast): Validates links on creation
"""

import secrets
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
from pathlib import Path


def generate_share_token() -> str:
    """Generate a secure, URL-safe share token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a token for storage (for security, we only store hashed tokens)."""
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass
class ShareableLink:
    """
    Represents a shareable link for one-click private dataset access.
    
    Unlike AccessGrant which requires email verification, ShareableLink
    provides direct access via a secret URL token. This is useful for:
    - Sharing with collaborators quickly
    - Embedding in papers/presentations
    - Reviewer access during peer review
    
    Attributes:
        id: Unique link identifier
        dataset_id: ID of the private dataset
        token_hash: SHA-256 hash of the share token (token not stored)
        created_by_email: Email of the person who created the link
        label: Optional human-readable label (e.g., "For Nature reviewers")
        created_at: When the link was created
        expires_at: When the link expires
        max_uses: Maximum number of times the link can be used (None = unlimited)
        use_count: Number of times the link has been used
        access_log: List of access events with timestamps and IPs
        revoked: Whether the link has been revoked
        last_used_at: When the link was last used
    """
    
    id: str
    dataset_id: str
    token_hash: str
    created_by_email: str
    created_at: str  # ISO format
    expires_at: str  # ISO format
    label: Optional[str] = None
    max_uses: Optional[int] = None
    use_count: int = 0
    access_log: List[Dict[str, str]] = None  # List of {timestamp, ip, user_agent}
    revoked: bool = False
    last_used_at: Optional[str] = None
    
    def __post_init__(self):
        if self.access_log is None:
            self.access_log = []
    
    @classmethod
    def create(
        cls,
        dataset_id: str,
        token: str,
        created_by_email: str,
        label: Optional[str] = None,
        expires_in_days: int = 30,
        max_uses: Optional[int] = None
    ) -> "ShareableLink":
        """
        Create a new shareable link.
        
        Args:
            dataset_id: ID of the private dataset
            token: The plain-text share token (will be hashed, NOT stored)
            created_by_email: Email of the person creating the link
            label: Optional descriptive label
            expires_in_days: How many days until the link expires
            max_uses: Maximum number of uses (None = unlimited)
            
        Returns:
            ShareableLink instance
        """
        now = datetime.utcnow()
        
        return cls(
            id=secrets.token_urlsafe(16),
            dataset_id=dataset_id,
            token_hash=hash_token(token),
            created_by_email=created_by_email.lower().strip(),
            label=label,
            created_at=now.isoformat(),
            expires_at=(now + timedelta(days=expires_in_days)).isoformat(),
            max_uses=max_uses,
        )
    
    def verify_token(self, token: str) -> bool:
        """
        Verify a token against this link.
        
        Args:
            token: The plain-text token to verify
            
        Returns:
            True if token matches and link is valid for use
        """
        if self.revoked:
            return False
        
        if self.is_expired():
            return False
        
        if self.max_uses is not None and self.use_count >= self.max_uses:
            return False
        
        return hash_token(token) == self.token_hash
    
    def is_expired(self) -> bool:
        """Check if link has expired."""
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.utcnow() > expires
    
    def is_valid(self) -> bool:
        """Check if link is valid for use (not expired, not revoked, not exhausted)."""
        if self.revoked:
            return False
        if self.is_expired():
            return False
        if self.max_uses is not None and self.use_count >= self.max_uses:
            return False
        return True
    
    def record_use(self, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> None:
        """Record a link usage event."""
        now = datetime.utcnow().isoformat()
        self.use_count += 1
        self.last_used_at = now
        self.access_log.append({
            "timestamp": now,
            "ip": ip_address or "unknown",
            "user_agent": user_agent or "unknown"
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShareableLink":
        """Create from dictionary."""
        return cls(**data)
    
    def to_public_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for public/API responses (excludes sensitive data)."""
        return {
            "id": self.id,
            "dataset_id": self.dataset_id,
            "label": self.label,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "max_uses": self.max_uses,
            "use_count": self.use_count,
            "last_used_at": self.last_used_at,
            "is_valid": self.is_valid(),
            "revoked": self.revoked
        }


class ShareableLinkStore:
    """
    Persistent storage for shareable links using JSON file.
    
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
            self._save_links({})
    
    def _load_links(self) -> Dict[str, Dict]:
        """Load all links from storage."""
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_links(self, links: Dict[str, Dict]) -> None:
        """Save all links to storage."""
        with open(self.storage_path, 'w') as f:
            json.dump(links, f, indent=2)
    
    def save(self, link: ShareableLink) -> None:
        """Save or update a link."""
        links = self._load_links()
        links[link.id] = link.to_dict()
        self._save_links(links)
    
    def get_by_id(self, link_id: str) -> Optional[ShareableLink]:
        """Get a link by ID."""
        links = self._load_links()
        if link_id in links:
            return ShareableLink.from_dict(links[link_id])
        return None
    
    def get_by_token(self, token: str) -> Optional[ShareableLink]:
        """
        Find a link by token.
        
        Searches all non-revoked, non-expired links for a matching token.
        
        Args:
            token: The plain-text token
            
        Returns:
            ShareableLink if found and valid, None otherwise
        """
        token_hashed = hash_token(token)
        links = self._load_links()
        
        for link_data in links.values():
            if link_data.get('token_hash') == token_hashed:
                link = ShareableLink.from_dict(link_data)
                if link.is_valid():
                    return link
        
        return None
    
    def get_links_for_dataset(self, dataset_id: str) -> List[ShareableLink]:
        """Get all links for a dataset."""
        links = self._load_links()
        
        result = []
        for link_data in links.values():
            if link_data['dataset_id'] == dataset_id:
                result.append(ShareableLink.from_dict(link_data))
        
        return result
    
    def get_links_by_creator(self, email: str) -> List[ShareableLink]:
        """Get all links created by an email."""
        email = email.lower().strip()
        links = self._load_links()
        
        result = []
        for link_data in links.values():
            if link_data['created_by_email'] == email:
                result.append(ShareableLink.from_dict(link_data))
        
        return result
    
    def revoke(self, link_id: str) -> bool:
        """Revoke a link by ID."""
        link = self.get_by_id(link_id)
        if link:
            link.revoked = True
            self.save(link)
            return True
        return False
    
    def revoke_all_for_dataset(self, dataset_id: str) -> int:
        """Revoke all links for a dataset. Returns count revoked."""
        links = self.get_links_for_dataset(dataset_id)
        count = 0
        for link in links:
            if not link.revoked:
                link.revoked = True
                self.save(link)
                count += 1
        return count
    
    def cleanup_expired(self) -> int:
        """Remove expired links. Returns count removed."""
        links = self._load_links()
        initial_count = len(links)
        
        links = {
            lid: ldata for lid, ldata in links.items()
            if not ShareableLink.from_dict(ldata).is_expired()
        }
        
        self._save_links(links)
        return initial_count - len(links)
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about stored links."""
        links = self._load_links()
        
        total = len(links)
        active = 0
        revoked = 0
        expired = 0
        exhausted = 0
        
        for link_data in links.values():
            link = ShareableLink.from_dict(link_data)
            if link.revoked:
                revoked += 1
            elif link.is_expired():
                expired += 1
            elif link.max_uses and link.use_count >= link.max_uses:
                exhausted += 1
            else:
                active += 1
        
        return {
            "total": total,
            "active": active,
            "revoked": revoked,
            "expired": expired,
            "exhausted": exhausted
        }
