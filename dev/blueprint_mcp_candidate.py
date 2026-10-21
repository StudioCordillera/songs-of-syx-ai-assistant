"""Developer-only read-only blueprint tools beside production MCP. Not packaged in the player."""
import json
import os
from pathlib import Path
from typing import Annotated
from pydantic import BaseModel,ConfigDict,Field
from mcp.types import ToolAnnotations
from mcp.server.mcpserver.exceptions import ToolError
from syx_mcp import Advisor,create_server
from dev.blueprint_examples import ROOT,load_registry

Version=Annotated[str,Field(strict=True,pattern=r'^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$')]
class SearchRequest(BaseModel):
    model_config=ConfigDict(strict=True,extra='forbid')
    query:Annotated[str,Field(min_length=1,max_length=300)]
    game_version:Version
    limit:Annotated[int,Field(ge=1,le=10)]=5
class GetRequest(BaseModel):
    model_config=ConfigDict(strict=True,extra='forbid')
    example_id:Annotated[str,Field(pattern=r'^[a-z][a-z0-9-]{0,63}$')]
    game_version:Version


def encoded(value):
    # Return literal JSON text so the measured UTF-8 payload is the actual MCP text content.
    raw=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':'))
    if len(raw.encode('utf-8'))>65536:raise ValueError('Blueprint result exceeds 64-KiB budget; use summary search')
    return raw


def candidate_server(advisor,registry):
    server=create_server(advisor)
    annotations=ToolAnnotations(readOnlyHint=True,destructiveHint=False,idempotentHint=True,openWorldHint=False)
    @server.tool(annotations=annotations)
    def search_blueprint_examples(request:SearchRequest)->str:
        """Discover original teaching schematics; no geometry or game state. Explicit version is a comparison, not installation/mod attestation. Never places anything."""
        try:
            return encoded({'scope':'developer_reference_catalog_no_live_state','results':registry.search(request.query,request.game_version,request.limit),
              'requested_game_version':request.game_version,'catalog_reviewed_game_version':registry.corpus.examples[0].game_version,'corpus_sha256':registry.corpus_hash,
              'catalog_report_sha256':registry.report_hash,'construction_validated':False,'execution_supported':False,
              'limits':['Original project teaching examples only; summary search omits geometry. No current world, UI selection, snapshot, installed mods, construction legality or optimum is attested.']})
        except ValueError as error:raise ToolError(str(error)) from None
    @server.tool(annotations=annotations)
    def get_blueprint_example(request:GetRequest)->str:
        """Fetch one original teaching grid with source/author/rights/catalog evidence and caveats. Not a build command or tested placement; other versions remain unknown."""
        try:
            return encoded({'scope':'developer_reference_catalog_no_live_state','requested_game_version':request.game_version,
              **registry.get(request.example_id,request.game_version)})
        except ValueError as error:raise ToolError(str(error)) from None
    return server


def isolated_state_dir(value):
    if not value:raise ValueError('Developer candidate requires explicit SYX_STATE_DIR under repository runtime/')
    original=Path(value)
    # Refuse symlink hops, including a link that happens to resolve back inside runtime.
    absolute=original.absolute()
    if any(p.is_symlink() for p in (absolute,*absolute.parents)):raise ValueError('Developer state directory cannot traverse symlinks')
    path=absolute.resolve();runtime=(ROOT/'runtime').resolve()
    if not path.is_relative_to(runtime) or path==runtime or not path.is_dir():raise ValueError('Use an existing disposable directory strictly under repository runtime/')
    return path


def main():
    state=isolated_state_dir(os.environ.get('SYX_STATE_DIR'))
    registry=load_registry()
    candidate_server(Advisor(state/'snapshot.json',state/'corpus.json'),registry).run(transport='stdio')

if __name__=='__main__':main()
