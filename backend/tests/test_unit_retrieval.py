"""Pure unit tests — no DB, no network."""

from app.retrieval.arabic import contains_arabic, normalize_arabic
from app.retrieval.reference import (
    parse_hadith_reference,
    parse_quran_reference,
    surah_name_matches,
)
from app.retrieval.service import _content_query, rrf_fuse


class TestNormalizeArabic:
    def test_strips_diacritics(self):
        assert normalize_arabic("بِسْمِ اللَّهِ") == "بسم الله"

    def test_unifies_alef_variants(self):
        assert normalize_arabic("أإآٱ") == "اااا"

    def test_folds_letters(self):
        assert normalize_arabic("مُوسَى") == "موسي"
        assert normalize_arabic("رَحْمَة") == "رحمه"

    def test_removes_tatweel_and_collapses_ws(self):
        assert normalize_arabic("الـــلّه  \n ربي") == "الله ربي"

    def test_contains_arabic(self):
        assert contains_arabic("ما هو الصبر؟")
        assert contains_arabic("patience الصبر mixed")
        assert not contains_arabic("patience in the quran")


class TestQuranReference:
    def test_numeric_colon(self):
        ref = parse_quran_reference("2:255")
        assert (ref.surah, ref.ayah_start, ref.ayah_end) == (2, 255, None)

    def test_numeric_space_and_range(self):
        ref = parse_quran_reference("2 1-5")
        assert (ref.surah, ref.ayah_start, ref.ayah_end) == (2, 1, 5)

    def test_surah_out_of_range(self):
        assert parse_quran_reference("115:1") is None

    def test_name_based(self):
        ref = parse_quran_reference("baqara 255")
        assert ref.surah is None
        assert ref.surah_name == "baqara"
        assert ref.ayah_start == 255

    def test_plain_question_is_not_a_reference(self):
        assert parse_quran_reference("what does the quran say about patience") is None
        assert parse_quran_reference("2:255 meaning") is None

    def test_named_verse_anywhere_in_query(self):
        for q in (
            "Which verse is Ayat al-Kursi?",
            "ayatul kursi",
            "explain the Throne Verse please",
        ):
            ref = parse_quran_reference(q)
            assert (ref.surah, ref.ayah_start) == (2, 255), q
        ref = parse_quran_reference("What is the verse of light?")
        assert (ref.surah, ref.ayah_start) == (24, 35)
        ref = parse_quran_reference("the verse of debt in the quran")
        assert (ref.surah, ref.ayah_start) == (2, 282)

    def test_named_verse_requires_word_boundaries(self):
        assert parse_quran_reference("what does kursi mean") is None
        assert parse_quran_reference("light verses about guidance") is None


class TestSurahNameMatching:
    def test_trailing_h_and_article(self):
        assert surah_name_matches("baqarah", "Al-Baqara", "The Cow")
        assert surah_name_matches("rahman", "Ar-Rahmaan", "The Beneficent")

    def test_doubled_letters(self):
        assert surah_name_matches("fatiha", "Al-Faatiha", "The Opening")
        assert surah_name_matches("yaseen", "Yaa-Seen", "Yaseen")

    def test_english_name(self):
        assert surah_name_matches("cow", "Al-Baqara", "The Cow")

    def test_no_match(self):
        assert not surah_name_matches("baqarah", "Al-Ikhlaas", "Sincerity")
        assert not surah_name_matches("na", "An-Naas", "Mankind")

    def test_tiny_name_does_not_false_match_inside_query(self):
        # "Man" (76) must not match the query "rahman"
        assert not surah_name_matches("rahman", "Al-Insaan", "Man")
        # but exact short names still work
        assert surah_name_matches("sad", "Saad", "The letter Saad")


class TestHadithReference:
    def test_simple(self):
        ref = parse_hadith_reference("bukhari 1")
        assert (ref.collection_key, ref.number) == ("bukhari", "1")

    def test_spaced_alias_and_letter_suffix(self):
        ref = parse_hadith_reference("Abu Dawud 2564a")
        assert (ref.collection_key, ref.number) == ("abudawud", "2564a")

    def test_non_reference(self):
        assert parse_hadith_reference("hadith about kindness") is None


class TestContentQuery:
    def test_strips_question_meta_words(self):
        assert _content_query("What does the Quran say about patience?") == "What does the about patience"

    def test_returns_original_when_nothing_stripped(self):
        assert _content_query('"seek help" patience') == '"seek help" patience'

    def test_returns_original_when_everything_stripped(self):
        assert _content_query("quran verse surah") == "quran verse surah"


class TestRrfFuse:
    def test_agreement_beats_single_signal(self):
        fused = rrf_fuse({"a": [1, 2, 3], "b": [2, 9, 1]})
        assert fused[2]["score"] > fused[3]["score"]
        assert fused[1]["score"] > fused[9]["score"]
        assert set(fused[2]["signals"]) == {"a", "b"}

    def test_empty(self):
        assert rrf_fuse({}) == {}
