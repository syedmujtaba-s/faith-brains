import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai.embeddings import VoyageEmbedder
from app.api import routes
from app.api.ratelimit import ask_limiter, search_limiter
from app.db.engine import get_session
from app.db.models import (
    Base,
    Edition,
    HadithCollection,
    HadithRecord,
    QuranTranslation,
    QuranVerse,
    Surah,
)
from app.main import app
from app.retrieval.arabic import normalize_arabic

ADMIN_URL = "postgresql+asyncpg://faithbrains:faithbrains@localhost:5433/faithbrains"
TEST_URL = "postgresql+asyncpg://faithbrains:faithbrains@localhost:5433/faithbrains_test"

AYAT_KURSI = (
    "اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ لَا تَأْخُذُهُ سِنَةٌ وَلَا نَوْمٌ"
)
BAQARAH_153 = "يَا أَيُّهَا الَّذِينَ آمَنُوا اسْتَعِينُوا بِالصَّبْرِ وَالصَّلَاةِ"
IKHLAS_1 = "قُلْ هُوَ اللَّهُ أَحَدٌ"
FATIHA_1 = "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ"
INTENTIONS_AR = "إِنَّمَا الأَعْمَالُ بِالنِّيَّاتِ"


async def _seed(sessionmaker) -> None:
    async with sessionmaker() as session:
        saheeh = Edition(
            key="english_saheeh",
            kind="quran_translation",
            name="Saheeh International",
            language="en",
            attribution="Saheeh International via QuranEnc.com",
            version="1.0-test",
        )
        session.add(saheeh)
        session.add_all(
            [
                Surah(
                    number=1,
                    name_arabic="الفاتحة",
                    name_english="The Opening",
                    name_transliterated="Al-Faatiha",
                    revelation_place="Meccan",
                    revelation_order=5,
                    ayah_count=7,
                ),
                Surah(
                    number=2,
                    name_arabic="البقرة",
                    name_english="The Cow",
                    name_transliterated="Al-Baqara",
                    revelation_place="Medinan",
                    revelation_order=87,
                    ayah_count=286,
                ),
                Surah(
                    number=112,
                    name_arabic="الإخلاص",
                    name_english="Sincerity",
                    name_transliterated="Al-Ikhlaas",
                    revelation_place="Meccan",
                    revelation_order=22,
                    ayah_count=4,
                ),
            ]
        )
        await session.flush()

        verses = {
            (1, 1): FATIHA_1,
            (2, 153): BAQARAH_153,
            (2, 255): AYAT_KURSI,
            (112, 1): IKHLAS_1,
        }
        translations = {
            (1, 1): "In the name of Allah, the Entirely Merciful, the Especially Merciful.",
            (2, 153): (
                "O you who have believed, seek help through patience and prayer. "
                "Indeed, Allah is with the patient."
            ),
            (2, 255): (
                "Allah - there is no deity except Him, the Ever-Living, the Sustainer of "
                "existence. Neither drowsiness overtakes Him nor sleep."
            ),
            (112, 1): 'Say, "He is Allah, [who is] One."',
        }
        for (s, a), arabic in verses.items():
            v = QuranVerse(
                surah_number=s,
                ayah_number=a,
                text_uthmani=arabic,
                text_simple=arabic,
                text_arabic_normalized=normalize_arabic(arabic),
                basmala_prefix=FATIHA_1 if s != 1 and a == 1 else None,
                juz=1 if s == 1 else (3 if s == 2 else 30),
                page=1 if s == 1 else (42 if s == 2 else 604),
            )
            session.add(v)
            await session.flush()
            session.add(
                QuranTranslation(verse_id=v.id, edition_id=saheeh.id, text=translations[(s, a)])
            )

        bukhari = HadithCollection(
            key="bukhari", name_english="Sahih al-Bukhari", name_arabic="صحيح البخاري"
        )
        session.add(bukhari)
        await session.flush()
        session.add(
            HadithRecord(
                collection_id=bukhari.id,
                hadith_number="1",
                book_number="1",
                book_name="Revelation",
                number_in_book="1",
                text_arabic=INTENTIONS_AR,
                text_arabic_normalized=normalize_arabic(INTENTIONS_AR),
                text_english=(
                    "The reward of deeds depends upon the intentions and every person will "
                    "get the reward according to what he has intended."
                ),
                gradings=[{"name": "Test Grader", "grade": "Sahih"}],
                reference_schemes={"in_book": "Book 1, Hadith 1"},
            )
        )
        await session.commit()


@pytest.fixture(scope="session")
async def test_engine():
    admin = create_async_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            exists = (
                await conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = 'faithbrains_test'")
                )
            ).scalar()
            if not exists:
                await conn.execute(text("CREATE DATABASE faithbrains_test"))
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Postgres not reachable ({exc}) — run: docker compose up -d db")
    finally:
        await admin.dispose()

    engine = create_async_engine(TEST_URL)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await _seed(async_sessionmaker(engine, expire_on_commit=False))
    yield engine
    await engine.dispose()


@pytest.fixture()
async def client(test_engine):
    sessionmaker = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_session():
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    ask_limiter.reset()
    search_limiter.reset()
    # Never hit the embeddings API from tests: force the vector signal off.
    original_embedder = routes.search_service.embedder
    routes.search_service.embedder = VoyageEmbedder(api_key="")
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        routes.search_service.embedder = original_embedder
        app.dependency_overrides.clear()
