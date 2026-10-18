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


# Developer posts checked directly, with speaker badges and historical context retained.
# These are original short summaries, not forum mirrors or claims of current-patch behavior.
SEEDS.extend([
    {
        'id':'developer-workload-estimate-2023',
        'title':'Workload and actual production — developer explanation',
        'url':'https://steamcommunity.com/app/1162750/discussions/0/3800525036429614132/',
        'kind':'forum','authority':'developer','author':'Gamatron',
        'retrieved_at':'2026-10-18T03:56:25Z','game_versions':[],
        'version_notes':'Developer reply dated 12 July 2023, comment #2. Later commenters dispute displayed estimates; exact game build and applicability to 0.71.44 are not established.',
        'text':'The developer distinguishes the displayed workload estimate from actual production. '
               'An indicated idle-worker fraction is an estimate, while realized output depends on time actually worked, '
               'production rate and bonuses. This historical explanation does not prove a current production bug '
               'or that changing worker counts will increase output. Inspect present staffing, inputs and recorded '
               'resource flows before advising the player.'
    },
    {
        'id':'developer-pasture-fertility-2021',
        'title':'Pasture fertility and animal capacity — historical developer answer',
        'url':'https://steamcommunity.com/app/1162750/discussions/0/2954914688097551706/',
        'kind':'forum','authority':'developer','author':'Gamatron',
        'retrieved_at':'2026-10-18T03:56:25Z','game_versions':[],
        'version_notes':'Developer answer dated 22 September 2021. Subsequent 2023 community comments discuss base fertility versus irrigation and disagree about some effects. No exact 0.71.44 compatibility established.',
        'text':'The developer explains pasture animal capacity in terms of fertility and area, connecting more '
               'animals with more workers and meat. This is historical evidence about capacity, not a current '
               'per-worker yield formula or proof that irrigation improves every pasture. Check installed room '
               'help and current-version evidence before applying it.'
    },
    {
        'id':'developer-faq-reference-navigation',
        'title':'Developer FAQ — finding game help and release notes',
        'url':'https://steamcommunity.com/app/1162750/discussions/0/3388408347654953100/',
        'kind':'forum','authority':'developer','author':'Gamatron',
        'retrieved_at':'2026-10-18T03:56:25Z','game_versions':[],
        'version_notes':'Opening developer post dated 28 May 2022, visibly edited 9 July 2023. Describes reference locations at that time; current launcher/Steam UI must be verified.',
        'text':'The developer FAQ points players to the game wiki and the in-game encyclopedia. '
               'It says launcher version numbers lead to release notes and describes selecting a previous '
               'game version through Steam beta settings to continue older saves. These are historical '
               'navigation instructions, not guarantees that old mechanics or saves work in the current build.'
    }
])


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
