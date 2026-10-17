"""Local game mailbox client. No desktop, network or arbitrary path access."""
from __future__ import annotations
import base64
import hashlib
import json
import os
from pathlib import Path
import struct
import threading
import time
import uuid
from urllib.parse import quote

from mcp.types import ImageContent, TextContent


class GameControl:
    def __init__(self, advisor, timeout: float = 10):
        self.advisor = advisor
        self.directory = advisor.snapshot_path.parent / 'control'
        self.timeout = timeout
        self.lock = threading.Lock()

    def request(self, operation: str, *, action_id: str | None = None, **fields) -> dict:
        identifier = str(uuid.UUID(action_id)) if action_id else str(uuid.uuid4())
        with self.lock:
            if operation != 'stop':
                state = self.advisor.status()
                if not state.get('live'):
                    raise ValueError('No fresh live game. Start the mod and load a game first.')
                fields.setdefault('session_id', state['session_id'])
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            intent = {'operation': operation, **{k: str(v) for k, v in fields.items()}}
            fingerprint = hashlib.sha256(json.dumps(intent, sort_keys=True).encode()).hexdigest()
            intent_path = self.directory / (identifier + '.intent')
            try:
                with intent_path.open('x') as out:
                    out.write(fingerprint)
            except FileExistsError:
                if intent_path.read_text() != fingerprint:
                    raise ValueError('Action ID was already used for different parameters')
            response = self.directory / (identifier + '.json')
            claimed = self.directory / (identifier + '.claimed')
            request = self.directory / (identifier + '.req')
            if not response.exists() and not claimed.exists() and not request.exists():
                values = {**intent, 'deadline': str(int((time.time() + self.timeout) * 1000))}
                body = '\n'.join(k + '=' + quote(v, safe='') for k, v in values.items())
                if len(body.encode('utf-8')) > 32768:
                    raise ValueError('Encoded request exceeds 32 KiB')
                temp = self.directory / (identifier + '.client-tmp')
                temp.write_text(body, encoding='utf-8')
                os.replace(temp, request)
            start = time.monotonic()
            while time.monotonic() - start < self.timeout:
                if response.exists():
                    from syx_mcp import load_json
                    result = load_json(response, 65536)
                    if not result.get('ok'):
                        raise ValueError(result.get('error', 'Game rejected the request'))
                    return result
                time.sleep(0.025)
            raise TimeoutError('Game did not acknowledge the request. Outcome may be uncertain; '
                               'do not repeat with a new action ID. Re-observe before deciding.')

    def content(self, result: dict) -> list:
        content = [TextContent(type='text', text=json.dumps(result))]
        image = result.get('image')
        if image:
            expected = str(uuid.UUID(result['action_id'])) + '.png'
            if image != expected:
                raise ValueError('Invalid image name from game bridge')
            with (self.directory / expected).open('rb') as file:
                raw = file.read(15 * 1024 * 1024 + 1)
            if len(raw) > 15 * 1024 * 1024 or raw[:8] != b'\x89PNG\r\n\x1a\n':
                raise ValueError('Invalid or oversized game screenshot')
            if len(raw)<24 or struct.unpack('>II', raw[16:24]) != (result['width'], result['height']):
                raise ValueError('Screenshot dimensions do not match observation')
            content.append(ImageContent(type='image', data=base64.b64encode(raw).decode(), mimeType='image/png'))
        return content

    def action(self, operation: str, session_id: str, grant_id: str, frame_id: str,
               action_id: str, x: int = 0, y: int = 0, value: str = '') -> list:
        if operation not in {'click', 'hover', 'scroll', 'key', 'text'}:
            raise ValueError('Unsupported game UI operation')
        if operation == 'click' and value not in {'left', 'right'}:
            raise ValueError('Click value must be left or right')
        if operation == 'scroll' and (not value.lstrip('-').isdigit() or not -5 <= int(value) <= 5):
            raise ValueError('Scroll value must be an integer from -5 to 5')
        if operation == 'text' and (len(value)>64 or any(ord(c)<32 or ord(c)>65535 for c in value)):
            raise ValueError('Text must be at most 64 printable BMP characters')
        return self.content(self.request(operation, action_id=action_id, session_id=session_id,
            grant_id=grant_id, frame_id=frame_id, x=x, y=y, value=value))
