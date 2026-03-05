#!/usr/bin/env python3
"""
Migrate to SQLite

Migrates existing JSON data (access_grants.json, shareable_links.json) to SQLite.
Also imports curated datasets from filesystem scan into the datasets table.

Usage:
    python scripts/migrate-to-sqlite.py [--db-path PATH] [--data-dir PATH] [--dry-run]

Options:
    --db-path PATH    Path to SQLite database (default: data/cellxgene.db)
    --data-dir PATH   Path to data directory (default: data)
    --dry-run         Show what would be migrated without making changes
"""

import argparse
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "landing-page" / "src"))

from services.database import Database, CURRENT_SCHEMA_VERSION


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_json_file(path: Path) -> dict:
    """Load JSON file, returning empty dict if not found."""
    if not path.exists():
        logger.info(f"  No file found at {path}")
        return {}
    
    try:
        with open(path, 'r') as f:
            data = json.load(f)
            logger.info(f"  Loaded {len(data)} records from {path}")
            return data
    except json.JSONDecodeError as e:
        logger.error(f"  Failed to parse {path}: {e}")
        return {}


def migrate_access_grants(db: Database, grants_path: Path, dry_run: bool) -> int:
    """Migrate access_grants.json to SQLite."""
    logger.info("Migrating access grants...")
    
    grants = load_json_file(grants_path)
    if not grants:
        return 0
    
    migrated = 0
    with db.transaction() as conn:
        for grant_id, grant_data in grants.items():
            if dry_run:
                logger.info(f"  [DRY RUN] Would migrate grant: {grant_id}")
                migrated += 1
                continue
            
            # Convert access_log from list of timestamps to separate log table entries
            access_log = grant_data.pop('access_log', [])
            
            # Insert grant
            conn.execute("""
                INSERT OR REPLACE INTO access_grants 
                (id, dataset_id, email, code_hash, created_at, expires_at, verified, verified_at, revoked)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                grant_data.get('id', grant_id),
                grant_data.get('dataset_id'),
                grant_data.get('email'),
                grant_data.get('code_hash'),
                grant_data.get('created_at'),
                grant_data.get('expires_at'),
                1 if grant_data.get('verified') else 0,
                grant_data.get('verified_at'),
                1 if grant_data.get('revoked') else 0,
            ))
            
            # Insert access log entries
            for timestamp in access_log:
                conn.execute("""
                    INSERT INTO access_grant_log (grant_id, accessed_at)
                    VALUES (?, ?)
                """, (grant_data.get('id', grant_id), timestamp))
            
            migrated += 1
            logger.info(f"  Migrated grant: {grant_id} ({len(access_log)} log entries)")
    
    return migrated


def migrate_shareable_links(db: Database, links_path: Path, dry_run: bool) -> int:
    """Migrate shareable_links.json to SQLite."""
    logger.info("Migrating shareable links...")
    
    links = load_json_file(links_path)
    if not links:
        return 0
    
    migrated = 0
    with db.transaction() as conn:
        for link_id, link_data in links.items():
            if dry_run:
                logger.info(f"  [DRY RUN] Would migrate link: {link_id}")
                migrated += 1
                continue
            
            # Convert access_log to separate log table entries
            access_log = link_data.pop('access_log', [])
            
            # Map created_by_email to the new schema
            created_by_email = link_data.get('created_by_email')
            
            conn.execute("""
                INSERT OR REPLACE INTO shareable_links 
                (id, dataset_id, token_hash, created_by_email, label, created_at, 
                 expires_at, max_uses, use_count, last_used_at, revoked)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                link_data.get('id', link_id),
                link_data.get('dataset_id'),
                link_data.get('token_hash'),
                created_by_email,
                link_data.get('label'),
                link_data.get('created_at'),
                link_data.get('expires_at'),
                link_data.get('max_uses'),
                link_data.get('use_count', 0),
                link_data.get('last_used_at'),
                1 if link_data.get('revoked') else 0,
            ))
            
            # Insert access log entries
            for log_entry in access_log:
                if isinstance(log_entry, dict):
                    conn.execute("""
                        INSERT INTO shareable_link_log (link_id, accessed_at, ip_address, user_agent)
                        VALUES (?, ?, ?, ?)
                    """, (
                        link_data.get('id', link_id),
                        log_entry.get('timestamp'),
                        log_entry.get('ip'),
                        log_entry.get('user_agent'),
                    ))
                else:
                    # Handle case where log is just timestamps
                    conn.execute("""
                        INSERT INTO shareable_link_log (link_id, accessed_at)
                        VALUES (?, ?)
                    """, (link_data.get('id', link_id), log_entry))
            
            migrated += 1
            logger.info(f"  Migrated link: {link_id} ({len(access_log)} log entries)")
    
    return migrated


def backup_json_files(grants_path: Path, links_path: Path, dry_run: bool) -> None:
    """Rename JSON files to .json.migrated as backup."""
    logger.info("Backing up JSON files...")
    
    for path in [grants_path, links_path]:
        if path.exists():
            backup_path = path.with_suffix('.json.migrated')
            if dry_run:
                logger.info(f"  [DRY RUN] Would rename {path} -> {backup_path}")
            else:
                shutil.move(path, backup_path)
                logger.info(f"  Renamed {path} -> {backup_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate JSON data to SQLite database"
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("data/cellxgene.db"),
        help="Path to SQLite database"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Path to data directory"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes"
    )
    
    args = parser.parse_args()
    
    # Resolve paths
    db_path = args.db_path.resolve()
    data_dir = args.data_dir.resolve()
    
    # Default JSON file locations (check common locations)
    grants_path = data_dir / "logs" / "access_grants.json"
    if not grants_path.exists():
        grants_path = data_dir / "access_grants.json"
    
    links_path = data_dir / "logs" / "shareable_links.json"
    if not links_path.exists():
        links_path = data_dir / "shareable_links.json"
    
    logger.info("=" * 60)
    logger.info("SQLite Migration Script")
    logger.info("=" * 60)
    logger.info(f"Database path: {db_path}")
    logger.info(f"Data directory: {data_dir}")
    logger.info(f"Grants file: {grants_path}")
    logger.info(f"Links file: {links_path}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("")
    
    if args.dry_run:
        logger.info("[DRY RUN MODE - No changes will be made]")
        logger.info("")
    
    # Initialize database
    if not args.dry_run:
        db = Database(db_path, logger)
        db.initialize()
    else:
        logger.info("[DRY RUN] Would create database schema")
        # Create a temporary in-memory database for validation
        db = Database(":memory:", logger)
        db.initialize()
    
    # Migrate data
    grants_count = migrate_access_grants(db, grants_path, args.dry_run)
    links_count = migrate_shareable_links(db, links_path, args.dry_run)
    
    # Backup JSON files
    if grants_count > 0 or links_count > 0:
        backup_json_files(grants_path, links_path, args.dry_run)
    
    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("Migration Summary")
    logger.info("=" * 60)
    logger.info(f"Access grants migrated: {grants_count}")
    logger.info(f"Shareable links migrated: {links_count}")
    
    if not args.dry_run:
        stats = db.get_stats()
        logger.info("")
        logger.info("Database statistics:")
        for table, count in stats.items():
            logger.info(f"  {table}: {count} records")
    
    logger.info("")
    logger.info("✓ Migration complete!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
