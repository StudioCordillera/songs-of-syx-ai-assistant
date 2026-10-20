"""Developer-only explicit task/Stop ownership for accepted target questions.

No watcher, polling worker, native control, provider setup or normal migration.
A caller owns one event loop, initialized queue/dispatch, MCP and history lifetime.
"""
import asyncio
from collections import OrderedDict

from dev.chat_target_queue import TargetAdmission, intent
from dev.chat_target_dispatch import TargetDispatch


class TargetTasks:
    MAX_ACTIVE = 8
    MAX_RECENT = 100

    def __init__(self, admission, dispatch):
        if (not isinstance(admission, TargetAdmission) or not isinstance(dispatch, TargetDispatch)
                or admission.queue is not dispatch.queue or admission.adapter is not dispatch.adapter):
            raise ValueError('One owned admission/dispatch queue and MCP adapter required')
        dispatch._ready()  # caller explicitly initializes disposable extensions
        self.admission, self.dispatch = admission, dispatch
        self._active = {}
        self._recent = OrderedDict()
        self._lock = asyncio.Lock()
        self._loop = None
        self._closed = False

    def _owner(self):
        loop = asyncio.get_running_loop()
        if self._loop is None: self._loop = loop
        if loop is not self._loop: raise ValueError('Task lane belongs to its original event loop')

    def _claimed(self, request):
        return self.dispatch.queue.db.execute('SELECT 1 FROM syx_target_dispatch WHERE request_id=?',
                                             (request['request_id'],)).fetchone() is not None

    def _view(self, request):
        ack = self.dispatch.queue.lookup(request)
        if ack is None: raise ValueError('No accepted request')
        row = self.dispatch.queue.db.execute('SELECT status FROM turns WHERE turn_id=? AND chat_id=?',
                                            (request['turn_id'],request['chat_id'])).fetchone()
        if row is None: raise ValueError('Accepted turn no longer exists')
        active = self._active.get(request['request_id'])
        running = active is not None and not active['task'].done()
        claimed = self._claimed(request)
        status = row[0]
        return dict(request_id=request['request_id'],chat_id=request['chat_id'],turn_id=request['turn_id'],
                    game_session=request['game_session'],accepted=True,turn_status=status,
                    owned_task_active=running,stop_requested=bool(active and active['stop_requested']),
                    dispatch_claimed=claimed,automatic_retry=False,
                    remote_outcome_unknown=claimed and status!='completed',
                    cleanup_pending=running and status in ('completed','failed','cancelled'),
                    last_attempt=self._attempt(request))

    def _attempt(self, request):
        cached = self._recent.get(request['request_id'])
        return cached[1] if cached and cached[0] == intent(**request)[1] else None

    def view(self, request):
        self._owner()
        request, _ = intent(**request)
        return self._view(request)

    def _completed(self, request, task):
        # Consume failures without retaining provider results, tracebacks or text.
        if task.cancelled(): outcome = 'cancelled'
        else:
            error = task.exception()
            outcome = 'returned' if error is None else 'failed'
        self._active.pop(request['request_id'], None)
        self._recent[request['request_id']] = (intent(**request)[1], outcome)
        self._recent.move_to_end(request['request_id'])
        while len(self._recent) > self.MAX_RECENT: self._recent.popitem(last=False)

    async def start(self, request):
        self._owner()
        request, _ = intent(**request)  # immutable intent before any await
        # Includes lock wait + MCP acceptance; a timeout never starts inference.
        async with asyncio.timeout(5):
            async with self._lock:
                if self._closed: raise ValueError('Task lane closed; no new work')
                active = self._active.get(request['request_id'])
                if active and active['request'] != request:
                    raise ValueError('Request ID still belongs to an owned task')
                prior = self.dispatch.queue.lookup(request)
                if prior is not None:
                    if request['request_id'] in self._active or self._claimed(request):
                        return self._view(request)  # exact retries never start another claimed workflow
                    if self._view(request)['turn_status'] != 'queued':
                        return self._view(request)
                if len(self._active) >= self.MAX_ACTIVE:
                    raise ValueError('Task lane full; draft retained, no new acceptance')
                await self.admission.accept(**request)
                if self._closed:
                    self.dispatch.queue.cancel(request)
                    raise ValueError('Task lane closed during acceptance; accepted turn cancelled before dispatch')
                # No await between durable acceptance and registering task ownership.
                # Chips/text are acknowledged separately by the native caller later.
                task = asyncio.create_task(self.dispatch.run(request))
                self._recent.pop(request['request_id'], None)
                self._active[request['request_id']] = dict(request=request,task=task,stop_requested=False)
                task.add_done_callback(lambda completed: self._completed(request, completed))
                return self._view(request)

    async def stop(self, request):
        self._owner()
        request, _ = intent(**request)
        view = self._view(request)  # exact accepted identity, never current selection
        owned = self._active.get(request['request_id'])
        if owned and owned['request'] != request:
            raise ValueError('Request ID still belongs to a different owned task')
        if owned is None or owned['task'].done():
            # An owned preclaim failure may leave accepted data queued. Stop it
            # explicitly, but never cancel another coordinator's unowned request.
            if view['turn_status']=='queued' and (owned is not None or self._attempt(request) is not None):
                self.dispatch.queue.cancel(request)
                return self._view(request)
            return view
        if view['turn_status'] in ('completed','failed','cancelled','interrupted'):
            return view  # pending cleanup cannot turn a completed answer into cancellation
        if not owned['stop_requested']:
            if view['turn_status']=='queued':
                self.dispatch.queue.cancel(request)  # cancellation before coroutine's first instruction
            owned['stop_requested'] = True
            owned['task'].cancel()  # one request; repeated Stop cannot interrupt cleanup again
        return self._view(request)  # Stop requested is not proof of remote cancellation

    async def close(self):
        self._owner()
        self._closed = True
        async with self._lock:
            # Wait for bounded in-flight acceptance before releasing dependencies.
            for record in list(self._active.values()):
                try:
                    await self.stop(record['request'])
                except Exception:
                    # History can disappear/become unavailable independently. Do
                    # not let one failed status lookup abandon other owned tasks.
                    if not record['task'].done() and not record['stop_requested']:
                        record['stop_requested'] = True
                        record['task'].cancel()
            tasks = {record['task'] for record in self._active.values()}
            if tasks:
                # Observe only: never force a second cancellation, detach, or forget cleanup.
                await asyncio.wait(tasks, timeout=2)
        return dict(closed=True,pending_owned_tasks=sum(not r['task'].done() for r in self._active.values()))
