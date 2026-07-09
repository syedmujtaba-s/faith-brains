"""Shared helpers for ingestion scripts. Every importer is idempotent."""

import hashlib
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import DATA_DIR
from app.db.models import Edition

RAW = DATA_DIR / "raw"


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


async def upsert_edition(session: AsyncSession, key: str, **fields) -> Edition:
    edition = (
        await session.execute(select(Edition).where(Edition.key == key))
    ).scalar_one_or_none()
    if edition is None:
        edition = Edition(key=key)
        session.add(edition)
    for name, value in fields.items():
        setattr(edition, name, value)
    edition.imported_at = datetime.now(timezone.utc)
    await session.flush()
    return edition
