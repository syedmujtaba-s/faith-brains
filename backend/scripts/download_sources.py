"""Download all source corpora to backend/data/raw/.

Idempotent: skips files that already exist (delete a file to re-fetch it).
Licensing notes for every source: docs/licensing.md.

Run: uv run python scripts/download_sources.py
"""

import asyncio
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import DATA_DIR  # noqa: E402

RAW = DATA_DIR / "raw"

TANZIL_FILES = {
    "tanzil/quran-uthmani.xml": (
        "https://tanzil.net/pub/download/index.php?quranType=uthmani&outType=xml&agree=true"
    ),
    "tanzil/quran-simple.xml": (
        "https://tanzil.net/pub/download/index.php?quranType=simple&outType=xml&agree=true"
    ),
    "tanzil/quran-data.xml": "https://tanzil.net/res/text/metadata/quran-data.xml",
}

QURANENC_EDITIONS = ["english_saheeh", "english_rwwad"]
QURANENC_SURA_API = "https://quranenc.com/api/v1/translation/sura/{key}/{sura}"

HADITH_BASE = "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1"
HADITH_COLLECTIONS = [
    "bukhari",
    "muslim",
    "abudawud",
    "tirmidhi",
    "nasai",
    "ibnmajah",
    "malik",
    "nawawi",
    "qudsi",
    "dehlawi",
]


async def fetch(client: httpx.AsyncClient, url: str) -> bytes:
    for attempt in range(5):
        try:
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code == 200:
                return resp.content
            if resp.status_code in (429, 500, 502, 503) and attempt < 4:
                await asyncio.sleep(2**attempt)
                continue
            resp.raise_for_status()
        except (httpx.TransportError, httpx.ReadTimeout):
            if attempt == 4:
                raise
            await asyncio.sleep(2**attempt)
    raise RuntimeError(f"unreachable: {url}")


def save(rel: str, content: bytes) -> None:
    path = RAW / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    print(f"  saved {rel} ({len(content):,} bytes)")


async def download_tanzil(client: httpx.AsyncClient) -> None:
    print("Tanzil (Quran Arabic text + metadata)")
    for rel, url in TANZIL_FILES.items():
        if (RAW / rel).exists():
            print(f"  {rel} exists, skipping")
            continue
        content = await fetch(client, url)
        if b"<quran" not in content[:2000] and b"<sura" not in content[:2000]:
            raise RuntimeError(f"{rel}: response does not look like Tanzil XML")
        save(rel, content)


async def quranenc_version(client: httpx.AsyncClient, key: str) -> str | None:
    """Best-effort lookup of the edition version (a QuranEnc license obligation to display)."""
    for url in (
        f"https://quranenc.com/api/v1/translations/list?language=english",
        f"https://quranenc.com/api/v1/translation/list?language=english",
    ):
        try:
            data = json.loads(await fetch(client, url))
        except Exception:
            continue
        items = data.get("translations", data) if isinstance(data, dict) else data
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and item.get("key") == key:
                    return str(item.get("version") or item.get("last_update") or "") or None
    return None


async def download_quranenc(client: httpx.AsyncClient) -> None:
    print("QuranEnc (English translations)")
    for key in QURANENC_EDITIONS:
        rel = f"quranenc/{key}.json"
        if (RAW / rel).exists():
            print(f"  {rel} exists, skipping")
            continue
        version = await quranenc_version(client, key)
        rows = []
        for sura in range(1, 115):
            data = json.loads(await fetch(client, QURANENC_SURA_API.format(key=key, sura=sura)))
            result = data.get("result", [])
            if not result:
                raise RuntimeError(f"{key}: sura {sura} returned no rows")
            rows.extend(result)
            if sura % 20 == 0:
                print(f"  {key}: sura {sura}/114")
        save(rel, json.dumps({"key": key, "version": version, "rows": rows}).encode())


async def download_hadith(client: httpx.AsyncClient) -> None:
    print("Hadith (fawazahmed0/hadith-api via jsDelivr)")
    editions_rel = "hadith/editions.json"
    if not (RAW / editions_rel).exists():
        save(editions_rel, await fetch(client, f"{HADITH_BASE}/editions.json"))
    editions = json.loads((RAW / editions_rel).read_text(encoding="utf-8"))

    for key in HADITH_COLLECTIONS:
        info = editions.get(key)
        if not info:
            print(f"  WARNING: collection '{key}' not in editions.json, skipping")
            continue
        wanted = {}
        for entry in info.get("collection", []):
            lang = entry.get("language", "").lower()
            if lang == "english" and "eng" not in wanted:
                wanted["eng"] = entry["name"]
            if lang == "arabic" and "ara" not in wanted:
                wanted["ara"] = entry["name"]
        for lang, edition_name in wanted.items():
            rel = f"hadith/{key}-{lang}.json"
            if (RAW / rel).exists():
                print(f"  {rel} exists, skipping")
                continue
            content = await fetch(client, f"{HADITH_BASE}/editions/{edition_name}.min.json")
            save(rel, content)


async def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(
        timeout=60, headers={"User-Agent": "FaithBrains/0.1 (educational; contact repo owner)"}
    ) as client:
        await download_tanzil(client)
        await download_quranenc(client)
        await download_hadith(client)
    print("\nAll downloads complete ->", RAW)


if __name__ == "__main__":
    asyncio.run(main())
