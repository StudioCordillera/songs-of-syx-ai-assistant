"""TEST ONLY: expose a declared truncated copy of real cached rows; leave game/transport untouched.

The timestamp/session/tick remain original. This simulates a partial cache, not an
actual production 10000-cell cap or a new live snapshot. Used only by the native verifier.
"""
import os
from pathlib import Path
from syx_mcp import Advisor,create_server


class PartialAdvisor(Advisor):
    def snapshot(self):
        s=super().snapshot().model_copy(deep=True)
        book=s.domains['world'].data.get('regional_output_bookkeeping') if s.domains['world'].data else None
        if book and book['coverage']=='partial':
            book['rows']=book['rows'][:100]
            book.update(truncated=True,cell_truncated=True,scanned_cells=len(book['rows']))
            book['scanned_regions']=len({r['region_id'] for r in book['rows']})
        return s


if __name__=='__main__':
    directory=Path(os.environ['SYX_STATE_DIR'])
    create_server(PartialAdvisor(directory/'snapshot.json',directory/'corpus.json')).run(transport='stdio')
