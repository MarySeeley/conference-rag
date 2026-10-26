"""Build public Speaker Theme Explorer data from the scraped talks.

The analysis uses TF-IDF across speakers, then boosts words that occur in
multiple talks by the same speaker. This highlights distinctive recurring
language without requiring another API or machine-learning dependency.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "scripts" / "output" / "talks.json"
OUTPUT_PATH = ROOT / "speaker-themes.json"
MIN_TALKS_PER_SPEAKER = 3
MIN_TALKS_PER_TERM = 2
THEMES_PER_SPEAKER = 10
EXAMPLES_PER_THEME = 2

# Common English and conference-specific words obscure what distinguishes one
# speaker from another. These are excluded before calculating TF-IDF.
STOP_WORDS = set(
    """
    about after again against all also am an and any are as at be because been
    before being between both but by can could did do does doesn doing down
    during each even every few for from further get give given go had has have
    having he her here hers herself him himself his how i if in into is isn it
    its itself just know like made make many may me more most much must my
    myself no nor not now of off on once one only or other our ours ourselves
    out over own people said same say says should so some such than that the
    their theirs them themselves then there these they thing things this those
    through time to too under until up us very was way we well were what when
    where which while who whom why will with would you your yours yourself
    yourselves
    amen apostle apostles brother brothers church conference dear elder elders
    father faith god gospel heavenly holy jesus christ latter lord message
    president prophet saint saints savior sister sisters spirit talk taught
    teaching teachings testimony today truth year years
    """.split()
)


def tokens(text: str) -> list[str]:
    """Return normalized content words from a talk."""
    return [
        word
        for word in re.findall(r"[a-z]+", text.lower().replace("’", "'"))
        if len(word) > 2 and word not in STOP_WORDS
    ]


def display_name(raw_name: str) -> str:
    """Remove the scraper's leading 'By' and normalize nonbreaking spaces."""
    name = raw_name.replace("\u00a0", " ").strip()
    return name[3:] if name.lower().startswith("by ") else name


def main() -> None:
    if not INPUT_PATH.exists():
        raise SystemExit(
            f"Missing {INPUT_PATH}. Run scripts/02_scrape_data.py first."
        )

    talks = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    talks_by_speaker: dict[str, list[dict]] = defaultdict(list)
    for talk in talks:
        talks_by_speaker[talk["speaker"]].append(talk)

    word_counts: dict[str, Counter[str]] = {}
    talk_counts: dict[str, Counter[str]] = {}
    speaker_frequency: Counter[str] = Counter()
    talk_tokens: dict[int, Counter[str]] = {}

    for speaker, speaker_talks in talks_by_speaker.items():
        words: Counter[str] = Counter()
        coverage: Counter[str] = Counter()
        for talk in speaker_talks:
            counts = Counter(tokens(talk["text"]))
            talk_tokens[id(talk)] = counts
            words.update(counts)
            coverage.update(counts.keys())
        word_counts[speaker] = words
        talk_counts[speaker] = coverage
        speaker_frequency.update(words.keys())

    total_speakers = len(talks_by_speaker)
    speakers = []

    for speaker, speaker_talks in talks_by_speaker.items():
        if len(speaker_talks) < MIN_TALKS_PER_SPEAKER:
            continue

        ranked_terms = []
        for term, mentions in word_counts[speaker].items():
            talks_with_term = talk_counts[speaker][term]
            if talks_with_term < MIN_TALKS_PER_TERM:
                continue

            inverse_speaker_frequency = (
                math.log((total_speakers + 1) / (speaker_frequency[term] + 1)) + 1
            )
            score = (
                (1 + math.log(mentions))
                * inverse_speaker_frequency
                * (1 + math.log(talks_with_term))
            )
            ranked_terms.append((score, term, mentions, talks_with_term))

        themes = []
        for _, term, mentions, talks_with_term in sorted(
            ranked_terms, reverse=True
        )[:THEMES_PER_SPEAKER]:
            matching_talks = sorted(
                (
                    (talk_tokens[id(talk)][term], talk)
                    for talk in speaker_talks
                    if talk_tokens[id(talk)][term]
                ),
                key=lambda item: (-item[0], item[1]["title"]),
            )
            examples = [
                {"title": talk["title"], "url": talk["url"]}
                for _, talk in matching_talks[:EXAMPLES_PER_THEME]
            ]
            themes.append(
                {
                    "term": term,
                    "mentions": mentions,
                    "talk_count": talks_with_term,
                    "examples": examples,
                }
            )

        speakers.append(
            {
                "name": display_name(speaker),
                "talk_count": len(speaker_talks),
                "themes": themes,
            }
        )

    speakers.sort(key=lambda item: item["name"])
    output = {
        "source_talk_count": len(talks),
        "method": "TF-IDF weighted by recurring use across a speaker's talks",
        "speakers": speakers,
    }
    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Analyzed {len(talks)} talks from {len(talks_by_speaker)} speakers")
    print(f"Included {len(speakers)} speakers with at least {MIN_TALKS_PER_SPEAKER} talks")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
