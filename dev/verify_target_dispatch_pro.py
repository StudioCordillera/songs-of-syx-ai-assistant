"""Explicit paid developer handoff check; caller owns copied-game MCP lifetime.

Never invoked by pytest/CI/default read fixtures. Key is loaded here only from an
explicit local file, never placed in the environment or sent to the game/MCP.
"""
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4

from syx_chat_service import read_key_file
from syx_chat_store import ChatStore
from syx_deepseek import DeepSeek
from dev.chat_target_candidate import canonical
from dev.chat_target_queue import TargetQueue, TargetAdmission
from dev.chat_target_dispatch import TargetDispatch, model_question


async def verify(adapter, directory, capture_id, expected_row, env_file):
    key = read_key_file(env_file)
    store = ChatStore(Path(directory)/'target-pro-history', secrets=(key,))
    rounds = 0
    workflow_count = 0
    inspected = 0
    evidence_hashes = []
    try:
        current = await adapter._status()
        chat = store.new(current['session_id'], model='deepseek-v4-pro')['chat_id']
        queue = TargetQueue(store);queue.initialize()
        admission = TargetAdmission(queue, adapter)
        expected_content = None
        class ObservedPro(DeepSeek):
            async def complete(self, messages, tools, on_text):
                nonlocal rounds, inspected
                assert self.model == 'deepseek-v4-pro'
                assert any(m.get('role') == 'user' and m.get('content', '').startswith(expected_content) for m in messages)
                assert key not in json.dumps(messages, ensure_ascii=False)
                inspected += 1
                rounds += 1  # attempts, including unknown remote outcomes; never retry here
                return await super().complete(messages, tools, on_text)
        def factory(chat_row):
            nonlocal workflow_count
            assert (chat_row['provider'],chat_row['route'],chat_row['model']) == ('deepseek','api','deepseek-v4-pro')
            workflow_count += 1
            return ObservedPro(key, model='deepseek-v4-pro')
        dispatch = TargetDispatch(queue, adapter, factory);dispatch.initialize()
        target = await adapter.stage(chat, 'tile', capture_id, limit=1)
        assert target['rows'] == [expected_row]
        questions = [
            ('Using only the attached historical tile observation, briefly report its tile coordinates, '
             'original tick and stored moisture values. Explain one limit on interpreting them as current facts. '
             'A short ordinary paragraph is enough; no tool is needed.', [target['attachment_id']]),
            ('Briefly explain why the earlier selected tile observation is historical evidence rather than '
             'proof of current values. Do not infer a selected room or a permanent world identity. No tool is needed.', [])]
        for text, ids in questions:
            request = dict(chat_id=chat, request_id=str(uuid4()), turn_id=str(uuid4()),
                           game_session=current['session_id'], text=text, attachment_ids=ids)
            await admission.accept(**request)
            evidence = queue.accepted_evidence(request['request_id'])
            expected_content = model_question(request, evidence)
            evidence_hashes.append(sha256(canonical(evidence)).hexdigest())
            await admission.acknowledge(request)
            answer = await dispatch.run(request)
            assert isinstance(answer,str) and answer.strip() and key not in answer
            before = rounds
            try: await dispatch.run(request)
            except ValueError as error: assert 'already claimed' in str(error)
            else: raise AssertionError('Claim replay was accepted')
            assert rounds == before
        turns = store.turns(chat);events = store.events(chat)
        assert len(turns)==2 and all(t['status']=='completed' for t in turns)
        assert sum(e['kind']=='user' for e in events)==2
        assert sum(e['kind']=='target_evidence' for e in events)==2
        assert sum(e['kind']=='dispatch_claimed' for e in events)==2
        assert adapter.preview(chat)==[]
        assert key not in json.dumps(events,ensure_ascii=False)
        return dict(passed=True,provider='deepseek',route='api',requested_model='deepseek-v4-pro',
                    provider_workflows=workflow_count,provider_round_attempts=rounds,
                    outgoing_original_evidence_checks=inspected,completed_turns=2,
                    selected_tile_rows=1,selected_row_matches_native_getter=True,
                    second_question_has_empty_target_envelope=True,duplicate_dispatch_refused=True,
                    original_question_events=2,accepted_envelope_sha256=evidence_hashes,
                    model_semantic_correctness_or_citation_quality_proven=False,
                    native_player_controls_tested=False)
    finally:
        store.close()
