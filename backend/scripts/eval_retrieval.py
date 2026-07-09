"""Retrieval quality eval: 50 natural-language Quran questions with gold verse refs.

Measures whether the retrieval layer surfaces at least one canonically-correct verse
for each question (hit@5 / hit@10 / MRR). Run before and after enabling embeddings to
see the semantic signal's contribution.

Run:  uv run python scripts/eval_retrieval.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.engine import get_sessionmaker  # noqa: E402
from app.retrieval.service import SearchService  # noqa: E402

K = 10

# (question, [acceptable verse refs]) — a hit is any gold ref in the top K results.
GOLD: list[tuple[str, list[str]]] = [
    ("What does the Quran say about patience?", ["2:153", "2:45", "3:200", "103:3", "2:155"]),
    ("Which verse is Ayat al-Kursi?", ["2:255"]),
    ("What does the Quran say about interest and usury?", ["2:275", "2:276", "2:278", "2:279", "3:130"]),
    ("Is alcohol forbidden in the Quran?", ["5:90", "5:91", "2:219"]),
    ("Which verses command fasting in Ramadan?", ["2:183", "2:184", "2:185"]),
    ("What does the Quran say about pilgrimage to Mecca?", ["3:97", "2:196", "2:197", "22:27"]),
    ("What is the reward for giving charity?", ["2:261", "2:262", "2:274", "57:18"]),
    ("Who is entitled to receive zakat?", ["9:60"]),
    ("What does the Quran say about justice?", ["4:135", "5:8", "16:90"]),
    ("How should I treat my parents according to the Quran?", ["17:23", "17:24", "31:14", "46:15"]),
    ("Is there compulsion in religion?", ["2:256"]),
    ("Should I despair of Allah's mercy after sinning?", ["39:53"]),
    ("What happens when you put your trust in Allah?", ["65:3", "3:159", "8:2"]),
    ("How does prayer stop bad deeds?", ["29:45"]),
    ("What does the Quran say about backbiting?", ["49:12"]),
    ("How do the servants of the Most Merciful walk?", ["25:63"]),
    ("Did the moon split?", ["54:1"]),
    ("Which surah tells the best of stories about Yusuf?", ["12:3", "12:4"]),
    ("What did Pharaoh do to the Children of Israel?", ["28:4", "2:49", "7:141"]),
    ("Does ease come after hardship?", ["94:5", "94:6"]),
    ("Will every soul taste death?", ["3:185", "21:35", "29:57"]),
    ("What happens if you are grateful to Allah?", ["14:7"]),
    ("What was the first revelation about reading?", ["96:1", "96:2", "96:3"]),
    ("Which dua asks for increase in knowledge?", ["20:114"]),
    ("Does Allah raise the ranks of people of knowledge?", ["58:11"]),
    ("What does the Quran say about modesty and covering?", ["24:31", "33:59", "24:30"]),
    ("How should orphans be treated?", ["93:9", "4:10", "4:2", "2:220"]),
    ("What does the Quran say about arrogance and pride?", ["31:18", "7:146", "17:37"]),
    ("Why did Allah create different peoples and tribes?", ["49:13"]),
    ("What is the verse of light?", ["24:35"]),
    ("Who is the best of planners?", ["8:30", "3:54"]),
    ("Were the heavens and the earth once joined together?", ["21:30"]),
    ("What is the Night of Decree?", ["97:1", "97:2", "97:3"]),
    ("What did Mary experience when giving birth to Jesus?", ["19:22", "19:23", "19:24", "19:16"]),
    ("Did Jesus speak in the cradle?", ["19:29", "19:30", "3:46"]),
    ("What happens on the Day of Judgment when the earth shakes?", ["99:1", "99:2", "99:4"]),
    ("How does the Quran describe the gardens of Paradise?", ["55:46", "55:54", "76:12", "76:13", "2:25"]),
    ("What is sincere repentance?", ["66:8", "25:70", "4:17"]),
    ("How vast is Allah's mercy?", ["7:156", "6:54", "39:53"]),
    ("What did Ayyub say when affliction touched him?", ["21:83", "21:84", "38:41"]),
    ("How should you respond to a greeting?", ["4:86"]),
    ("What does the Quran say about killing an innocent soul?", ["5:32", "17:33", "25:68"]),
    ("Is suicide forbidden in the Quran?", ["4:29"]),
    ("What sign of Allah is in the love between spouses?", ["30:21"]),
    ("What is the longest verse about recording debts?", ["2:282"]),
    ("Woe to those who give short measure in trade?", ["83:1", "83:2", "83:3"]),
    ("Is Allah closer to us than our jugular vein?", ["50:16"]),
    ("Why were death and life created?", ["67:2"]),
    ("Why did Allah create jinn and mankind?", ["51:56"]),
    ("Do hearts find rest in the remembrance of Allah?", ["13:28"]),
]


async def run() -> None:
    service = SearchService()
    if service.embedder.available:
        e = service.embedder
        print(f"mode: HYBRID (vector signal ON — {type(e).__name__} {e.model}, dim={e.dim})\n")
    else:
        print("mode: LEXICAL BASELINE (vector signal OFF — no VOYAGE_API_KEY)\n")

    hits5 = hits10 = 0
    mrr_total = 0.0
    misses: list[tuple[str, list[str], list[str]]] = []

    async with get_sessionmaker()() as session:
        for question, gold in GOLD:
            outcome = await service.search(session, question, scope="quran", k=K)
            refs = [r["reference"] for r in outcome["results"]]
            rank = next((i + 1 for i, ref in enumerate(refs) if ref in gold), None)
            if rank is not None:
                mrr_total += 1.0 / rank
                hits10 += 1
                if rank <= 5:
                    hits5 += 1
                marker = f"HIT @{rank}"
            else:
                misses.append((question, gold, refs[:5]))
                marker = "MISS"
            print(f"[{marker:>7}] {question}")

    n = len(GOLD)
    print(f"\n=== {n} questions, top-{K}, scope=quran ===")
    print(f"hit@5:  {hits5}/{n}  ({hits5 / n:.0%})")
    print(f"hit@10: {hits10}/{n}  ({hits10 / n:.0%})")
    print(f"MRR:    {mrr_total / n:.3f}")

    if misses:
        print(f"\n--- {len(misses)} misses ---")
        for question, gold, got in misses:
            print(f"Q: {question}\n   wanted {gold}\n   got    {got}")


if __name__ == "__main__":
    asyncio.run(run())
