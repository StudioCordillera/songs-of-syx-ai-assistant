from syx_knowledge import install_seed
from syx_mcp import Advisor

def test_seed_authority_and_versions(tmp_path):
    assert install_seed(tmp_path)==11
    assert install_seed(tmp_path)==11
    advisor=Advisor(tmp_path/'snapshot.json',tmp_path/'corpus.json')
    hit=advisor.search('trade','0.71.44')['results'][0]
    assert hit['authority']=='official' and hit['version_compatibility']=='family_match'
    assert '529882384083977659' in hit['url']
    guide=advisor.search('farms', '0.71.44', authority='community')['results'][0]
    assert guide['version_compatibility']=='family_match'
    historic=advisor.search('food', authority='developer')['results'][0]
    assert historic['version_compatibility']=='unknown'


def test_reviewed_player_question_retrieval(tmp_path):
    install_seed(tmp_path)
    advisor=Advisor(tmp_path/'snapshot.json',tmp_path/'corpus.json')
    cases={
        'trade tariffs logistics':'official-v71-trade',
        'law punishments loyalty':'official-v71-law',
        'parents infants nursery':'official-v71-families',
        'eatery red blue hungry':'steam-developer-eatery-overlay-2022',
        'workload workers idle production':'developer-workload-estimate-2023',
        'pasture fertility animals':'developer-pasture-fertility-2021',
        'release notes previous version':'developer-faq-reference-navigation',
        'farms moisture hunting':'steam-v71-starting-economy',
        'warehouse fetch priority radius':'steam-v71-logistics-nerond',
        'loading unloading stations loop':'steam-v71-logistics-nerond',
    }
    for question,expected in cases.items():
        result=advisor.search(question,'0.71.44',limit=1)['results'][0]
        assert result['id']==expected,(question,result['id'])
        assert result['url'].startswith('https://') and result['version_notes']
        assert result['version_compatibility'] in {'family_match','unknown'}
    assert not advisor.search('quasar hyperdrive')['results']


def test_install_preserves_existing_evidence(tmp_path):
    import json
    install_seed(tmp_path)
    path=tmp_path/'corpus.json'
    sources=json.loads(path.read_text())
    sources[0]['text']='User reviewed replacement, keep it.'
    sources[0]['retrieved_at']='2025-01-01T00:00:00Z'
    path.write_text(json.dumps(sources))
    install_seed(tmp_path)
    found=next(s for s in json.loads(path.read_text()) if s['id']==sources[0]['id'])
    assert found['text']==sources[0]['text'] and found['retrieved_at']==sources[0]['retrieved_at']


def test_upgrade_adds_reviewed_sources_without_replacing_local_evidence(tmp_path):
    import json
    install_seed(tmp_path)
    path=tmp_path/'corpus.json'
    added={'official-v71-research-education','official-v71-service-fetch-treatment'}
    prior=[s for s in json.loads(path.read_text()) if s['id'] not in added]
    prior[0]['text']='Locally reviewed evidence must survive the upgrade.'
    prior[0]['retrieved_at']='2025-01-01T00:00:00Z'
    local={**prior[0],'id':'local-reviewed-guide'}
    prior.append(local)
    path.write_text(json.dumps(prior))
    assert install_seed(tmp_path)==12
    upgraded={s['id']:s for s in json.loads(path.read_text())}
    assert added<=upgraded.keys()
    for original in prior:assert upgraded[original['id']]==original
    assert {upgraded[s]['retrieved_at'] for s in added}=={'2026-10-18T11:15:21Z'}
