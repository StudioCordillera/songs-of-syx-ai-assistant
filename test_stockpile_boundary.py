"""Reject unsafe/changed candidate reader bytecode without loading game classes."""
import pytest
from dev.review_stockpile_boundary import stored_reader


@pytest.mark.parametrize('instruction', [
    'putfield #1', 'putstatic #2', 'iastore', 'aastore', 'new #3', 'newarray int',
    'anewarray #4', 'multianewarray #5, 2', 'goto 0', 'ifne 0', 'tableswitch',
    'lookupswitch', 'invokedynamic #6',
])
def test_candidate_guard_refuses_writes_allocations_loops_and_dynamic_dispatch(instruction):
    with pytest.raises(ValueError):
        stored_reader('  0: aload_0\n  4: '+instruction+'\n  8: ireturn')


def test_candidate_guard_requires_semantic_markers_but_allows_forward_null_branch():
    body='  0: aload_0\n  1: ifnonnull 9\n  4: getfield #1 // Field ams:[I\n  9: iaload\n  10: ireturn'
    stored_reader(body, ('ams:[I', 'iaload'))
    with pytest.raises(ValueError, match='marker missing'):
        stored_reader(body, ('StockpileInstance.tdata:[[I',))
