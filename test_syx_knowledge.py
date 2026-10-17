from syx_knowledge import install_seed
from syx_mcp import Advisor

def test_seed_authority_and_versions(tmp_path):
    assert install_seed(tmp_path)==5
    assert install_seed(tmp_path)==5
    advisor=Advisor(tmp_path/'snapshot.json',tmp_path/'corpus.json')
    hit=advisor.search('trade','0.71.44')['results'][0]
    assert hit['authority']=='official' and hit['version_compatibility']=='family_match'
    assert '529882384083977659' in hit['url']
    guide=advisor.search('farms', '0.71.44', authority='community')['results'][0]
    assert guide['version_compatibility']=='family_match'
    historic=advisor.search('food', authority='developer')['results'][0]
    assert historic['version_compatibility']=='unknown'
