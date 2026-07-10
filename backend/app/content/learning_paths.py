"""Curated learning paths — ordered steps over verses/hadith already in the corpus.

Every reference here must exist in the ingested data (quran "s:a", hadith
"collection number"). Step keys are stable identifiers persisted in
path_progress; never rename them once shipped.
"""

PATHS: list[dict] = [
    {
        "key": "salah-basics",
        "title": "Salah: The Daily Connection",
        "description": "Why Muslims pray, what prayer protects you from, and the reward of praying together.",
        "steps": [
            {"key": "help-through-prayer", "title": "Seek help through patience and prayer", "kind": "quran", "reference": "2:153"},
            {"key": "prayer-restrains", "title": "Prayer restrains wrongdoing", "kind": "quran", "reference": "29:45"},
            {"key": "fixed-times", "title": "Prayer at fixed times", "kind": "quran", "reference": "4:103"},
            {"key": "five-pillars", "title": "Prayer among the five pillars", "kind": "hadith", "reference": "bukhari 8"},
            {"key": "congregation", "title": "The reward of praying together", "kind": "hadith", "reference": "bukhari 645"},
        ],
    },
    {
        "key": "ramadan-fasting",
        "title": "Ramadan & Fasting",
        "description": "The month of the Quran: why fasting was prescribed and what makes its nights special.",
        "steps": [
            {"key": "fasting-prescribed", "title": "Fasting is prescribed for you", "kind": "quran", "reference": "2:183"},
            {"key": "month-of-quran", "title": "The month the Quran was sent down", "kind": "quran", "reference": "2:185"},
            {"key": "night-of-decree", "title": "The Night of Decree", "kind": "quran", "reference": "97:1"},
            {"key": "fasting-faith", "title": "Fasting with faith and hope of reward", "kind": "hadith", "reference": "bukhari 38"},
        ],
    },
    {
        "key": "quran-essentials",
        "title": "Meeting the Quran",
        "description": "The opening, the greatest verse, pure monotheism, and the first revelation.",
        "steps": [
            {"key": "opening", "title": "The Opening", "kind": "quran", "reference": "1:1"},
            {"key": "ayat-al-kursi", "title": "Ayat al-Kursi — the greatest verse", "kind": "quran", "reference": "2:255"},
            {"key": "sincerity", "title": "Say: He is Allah, One", "kind": "quran", "reference": "112:1"},
            {"key": "first-revelation", "title": "The first revelation", "kind": "quran", "reference": "96:1"},
            {"key": "learn-teach", "title": "The best of you learn and teach it", "kind": "hadith", "reference": "bukhari 5027"},
        ],
    },
    {
        "key": "character",
        "title": "Character (Akhlaq)",
        "description": "How the Quran and Sunnah shape daily conduct: speech, humility, anger, and kindness.",
        "steps": [
            {"key": "no-backbiting", "title": "Do not backbite", "kind": "quran", "reference": "49:12"},
            {"key": "walk-humbly", "title": "The servants of the Most Merciful", "kind": "quran", "reference": "25:63"},
            {"key": "no-arrogance", "title": "Do not turn your cheek in pride", "kind": "quran", "reference": "31:18"},
            {"key": "return-greeting", "title": "Return the greeting better", "kind": "quran", "reference": "4:86"},
            {"key": "love-for-brother", "title": "Love for your brother what you love for yourself", "kind": "hadith", "reference": "bukhari 13"},
            {"key": "do-not-be-angry", "title": "Do not become angry", "kind": "hadith", "reference": "bukhari 6116"},
            {"key": "smile-charity", "title": "A smile is charity", "kind": "hadith", "reference": "tirmidhi 1956"},
        ],
    },
]

PATHS_BY_KEY = {p["key"]: p for p in PATHS}
