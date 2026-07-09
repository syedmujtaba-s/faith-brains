# Data sources & licensing obligations

Last reviewed: 2026-07-09. This file records where every piece of corpus data comes from and what
the license obliges us to do. **Treat the obligations as release blockers, not niceties.**

## Quran — Arabic text

- **Source:** [Tanzil Project](https://tanzil.net/download/) — Uthmani + Simple scripts, XML.
- **License:** verbatim redistribution only; changing the text is not allowed; credit
  "Tanzil Project" clearly; link to https://tanzil.net.
- **Obligations in-app:** attribution + link in the frontend footer/about page; displayed Arabic
  stays verbatim (search normalization happens in a separate internal column).
- **Basmala:** Tanzil prepends the basmala to ayah 1 of suras 2–114 (except 9). The importer splits
  it into `basmala_prefix`; verse text remains verbatim Tanzil text otherwise.

## Quran — metadata

- **Source:** [Tanzil quran-data.xml](https://tanzil.net/res/text/metadata/quran-data.xml) (juz,
  hizb quarters, rukus, pages, sajdas, revelation order). License: cc-by.

## Quran — English translations

- **Source:** [QuranEnc.com](https://quranenc.com) — Saheeh International (`english_saheeh`) and
  Rowwad Translation Center (`english_rwwad`).
- **License conditions (from QuranEnc):**
  1. Clearly refer to the publisher and the source (QuranEnc.com).
  2. **No modification, addition, or deletion of the content** — even typo fixes are not allowed.
  3. Mention the translation **version number** when re-publishing.
  4. Update to the latest version issued from the source (periodic re-sync).
- **Obligations in-app:** attribution + edition version displayed; re-sync procedure documented;
  the `editions` table stores `version` for exactly this reason.
- **Fallback:** Pickthall (1930) is public domain worldwide (US as of 2026-01-01) — unconditional.

## Hadith

- **Source:** [fawazahmed0/hadith-api](https://github.com/fawazahmed0/hadith-api) via jsDelivr CDN.
  Collections: Bukhari, Muslim, Abu Dawud, Tirmidhi, Nasa'i, Ibn Majah, Malik, Nawawi 40, Qudsi 40,
  Dehlawi 40. Arabic + English + multi-grader gradings (Al-Albani, Zubair Ali Zai, Shuaib
  al-Arnaut, et al.).
- **License:** repo is The Unlicense (public domain dedication). **However** the copyright status of
  the underlying English translations (Muhsin Khan's Bukhari, Siddiqui's Muslim, Darussalam-lineage
  Sunan texts) is unresolved upstream (repo issue #129 unanswered). Formal status of these
  translations is "all rights reserved" at their print publishers; de facto they are redistributed
  ecosystem-wide with no observed enforcement.
- **Decision:** acceptable for development and private beta. **Before public launch:** obtain
  written clearance (Darussalam / sunnah.com / translators) or trim to collections whose English
  text is cleared (Nawawi 40 variants, public-domain-aged translations).
- **Do NOT ingest from:** sunnah.com (About page: "We do not permit the scraping of our data, nor
  mass reproduction of entire books or collections") or dorar.net (terms prohibit off-site use of
  the Hadith Encyclopedia).

## Runtime cross-check APIs (not bulk sources)

- alquran.cloud — cross-checking imports only (community-run, soft rate limits).
- Quran Foundation Content API — OAuth2-gated; terms prohibit bulk compilation.

## Attribution strings (frontend footer/about — copy exactly)

> Quran text: Tanzil Project (tanzil.net). Translations: Saheeh International and Rowwad
> Translation Center via QuranEnc.com (edition versions shown per translation). Hadith data:
> open hadith-api dataset. FaithBrains is an educational tool and not a source of religious rulings.
