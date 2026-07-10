"""User personas — self-chosen learning roles that tune the assistant's voice.

Persona keys are stable identifiers persisted in learners.persona and sent by
clients; never rename them once shipped. A persona changes ONLY style and depth
(prompt_hint), suggested questions, and recommended paths — it must never relax
the grounding or religious-authority rules, and it is not belief profiling.

Every suggested question must be answerable from the ingested corpus, and every
recommended path key must exist in app.content.learning_paths.
"""

PERSONAS: list[dict] = [
    {
        "key": "learner",
        "label": "Learner",
        "tagline": "Plain-language answers to your questions, with every source cited.",
        "prompt_hint": (
            "Audience: a general learner exploring Islam's teachings.\n"
            "- Explain in plain, everyday language; briefly define any Arabic or "
            "technical term the first time it appears.\n"
            "- Favour practical understanding over academic detail, and keep the "
            "answer compact.\n"
            "- Close longer answers with the single most important takeaway from "
            "the cited sources."
        ),
        "suggested_questions": [
            "What does the Quran say about patience in hard times?",
            "How should I treat my parents?",
            "What is the reward for giving charity?",
            "Why do Muslims fast in Ramadan?",
            "What does Islam teach about honesty?",
        ],
        "recommended_paths": ["quran-essentials", "character"],
    },
    {
        "key": "student",
        "label": "Student of knowledge",
        "tagline": "Precise, source-linked study with references and gradings.",
        "prompt_hint": (
            "Audience: a student of knowledge who wants precision.\n"
            "- Cite with full precision: name the surah and verse number, and the "
            "hadith collection and number, exactly as given in the sources.\n"
            "- Mention hadith gradings whenever the sources include them.\n"
            "- Use standard terminology (with a brief gloss where helpful) and note "
            "nuances visible in the sources themselves, such as differing "
            "narrations — without adding outside material."
        ),
        "suggested_questions": [
            "Which hadith says actions are judged by intentions?",
            "What does Ayat al-Kursi say, and where is it found?",
            "Which verses pair patience with prayer?",
            "Which hadith lists the five pillars of Islam?",
            "What was the first revelation of the Quran?",
        ],
        "recommended_paths": ["quran-essentials", "salah-basics"],
    },
    {
        "key": "educator",
        "label": "Educator / Imam",
        "tagline": "Structured, citable material ready for classes and khutbahs.",
        "prompt_hint": (
            "Audience: an educator or imam preparing to teach this material.\n"
            "- Organise the answer for easy relay: the key point first, then each "
            "supporting verse or hadith with its full citation.\n"
            "- Keep quotations exact so they can be read aloud or copied into "
            "teaching material; include hadith gradings when the sources provide "
            "them.\n"
            "- Where several sources make the same point, group them rather than "
            "repeating the explanation."
        ),
        "suggested_questions": [
            "Which verses and hadith teach kindness to parents and family?",
            "What do the sources say about controlling anger?",
            "Which hadith encourages learning and teaching the Quran?",
            "What does the Quran say about justice and fairness?",
            "What is the reward of praying in congregation?",
        ],
        "recommended_paths": ["character", "salah-basics"],
    },
    {
        "key": "new_muslim",
        "label": "New Muslim",
        "tagline": "A gentle, accurate introduction — one step at a time.",
        "prompt_hint": (
            "Audience: someone new to Islam.\n"
            "- Be gentle, welcoming, and unhurried; assume no prior knowledge and "
            "explain every Arabic term in plain words.\n"
            "- Focus on the essentials shown in the sources and avoid overwhelming "
            "detail; reassure the reader that learning gradually is normal.\n"
            "- Take extra care not to frame any practice as a personal obligation "
            "or verdict for the reader; describe what the sources teach and warmly "
            "encourage learning with a local scholar or community."
        ),
        "suggested_questions": [
            "What are the five pillars of Islam?",
            "Why do Muslims pray five times a day?",
            "What is the Quran and how was it first revealed?",
            "What does the Quran say about Allah's mercy?",
            "What happens during Ramadan?",
        ],
        "recommended_paths": ["quran-essentials", "salah-basics", "ramadan-fasting"],
    },
]

PERSONAS_BY_KEY = {p["key"]: p for p in PERSONAS}
