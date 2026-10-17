"""Install a small reviewed starter corpus of original summaries, never full guides."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

SEEDS = [
    {
        'id': 'steam-v71-starting-economy',
        'title': 'Tips & Tricks from my first 130 hours — early economy and logistics',
        'url': 'https://steamcommunity.com/sharedfiles/filedetails/?id=3776333166',
        'kind': 'guide', 'authority': 'community', 'author': 'ApathicAlpaca',
        'game_versions': ['0.71'],
        'version_notes': 'Author describes v71; exact 0.71.44 compatibility is unverified. '
                         'Steam extraction includes removal/incompatibility notice text; verify live page status.',
        'text': 'The author recommends gathering wild food and hunting during the early settlement phase, '
                'then expanding into farms as population grows. They recommend inspecting moisture before '
                'placing farms. For trade logistics, import and export depots should be near the industries '
                'they serve. The guide suggests checking the Goods interface to compare offers from other '
                'nations. These are community recommendations, not guaranteed optimal rules; verify them '
                'against current staffing, resource flows, race preferences and game version.'
    },
    {
        'id': 'steam-developer-eatery-overlay-2022',
        'title': 'Meaning of red/blue grid when selecting eatery? — developer reply',
        'url': 'https://steamcommunity.com/app/1162750/discussions/0/4841941418359552221/',
        'kind': 'forum', 'authority': 'developer', 'author': 'Gamatron',
        'game_versions': [],
        'version_notes': 'Archived 2022 developer reply. Applicability to 0.71.44 is unknown; timestamp time zone is not established.',
        'text': 'A developer reply explains that red cells on an eatery overlay mark places where hungry '
                'people could not obtain service because an eatery was full or lacked food. This is '
                'historical evidence and requires confirmation in the current game.'
    }
]


# Original summaries of the official V71 release announcement, under 150 words total.
# Content verified via Steam's full-text announcement archive; canonical link is retained.
for topic, text in {
    'law': 'V71 redesigned law around the effects of crime punishments on happiness and loyalty. '
           'Guard coverage and related law infrastructure modify those effects. '
           'The announcement presents happiness and fear-based loyalty as alternative approaches to control.',
    'families': 'Most races gained natural reproduction in V71. Parents care for infants before they become children. '
                'Reproduction settings can limit growth and cause unhappiness among subjects who want children. '
                'The update includes family trees and a shared nursery that reduces child mortality.',
    'trade': 'V71 changed trade to include percentage tariffs in both directions and per-item logistics costs. '
             'The release announcement describes early trading as more expensive and notes that emissary placement '
             'affects trade opportunities. Technology costs and recipe-specific research also changed.'
}.items():
    SEEDS.append({
        'id': 'official-v71-'+topic, 'title': 'V71 official release notes — '+topic,
        'url': 'https://steamcommunity.com/games/1162750/announcements/detail/529882384083977659',
        'kind': 'official', 'authority': 'official', 'author': 'Gamatron / Songs of Syx',
        'game_versions': ['0.71'],
        'version_notes': 'V71 release announcement; later patch changes require verification. Section: '+topic+'. '
            'Text checked in Steam full-text announcement archive; canonical announcement URL retained.',
        'text': text, 'retrieved_at': '2026-10-17T19:00:51Z'
    })


def install_seed(directory: Path):
    from syx_mcp import Source, load_json
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'corpus.json'
    existing = load_json(path, 8*1024*1024) if path.exists() else []
    by_id = {item.id: item.model_dump(mode='json') for item in map(Source.model_validate, existing)}
    for record in SEEDS:
        # Retrieval date records the source check for these authored summaries, not today's reinstallation.
        source = Source.model_validate({'retrieved_at': '2026-10-17T18:00:00Z', **record})
        by_id.setdefault(source.id, source.model_dump(mode='json'))
    temp = directory / 'corpus.seed-tmp'
    temp.write_text(json.dumps(list(by_id.values()), indent=2) + '\n')
    os.replace(temp, path)
    return len(by_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', type=Path, default=Path(os.environ.get(
        'SYX_STATE_DIR', Path.home()/'.local/share/syx-assistant')))
    args = parser.parse_args()
    print(f'Installed starter corpus; {install_seed(args.state_dir)} records. See version warnings in results.')

if __name__ == '__main__':
    main()
