"""Bounded, ordered background recording for simulation demonstration collection.

The existing spool still compresses, fsyncs, and publishes each file. Only the
caller waiting for those writes moves out of the control loop. Ready metadata
is never published until every append has completed successfully.
"""
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from time import perf_counter


class AsyncEpisodeSpool:
    def __init__(self, spool, *, max_pending=8):
        if type(max_pending) is not int or max_pending < 1:
            raise ValueError('positive integer queue capacity required')
        self._spool = spool
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='simulation-recording')
        self._pending = deque()
        self._capacity = max_pending
        self._failure = None
        self.closed = False
        self._stats = dict(mode='async-durable-v1', capacity=max_pending, submitted=0,
                           max_pending=0, backpressure_seconds=0., finish_wait_seconds=0.)

    @property
    def directory(self):
        return self._spool.directory

    @property
    def count(self):
        # Collection only reads this after finish(), when all writes are done.
        return self._spool.count

    @property
    def statistics(self):
        return dict(self._stats, written=self._spool.count, closed=self.closed)

    def _wait_one(self):
        try:
            self._pending.popleft().result()
        except BaseException as exc:
            self._failure = exc
            raise

    def append(self, *args, **kwargs):
        if self.closed:
            raise RuntimeError('recorder is closed')
        if self._failure is not None:
            raise self._failure
        while self._pending and self._pending[0].done():
            self._wait_one()
        if len(self._pending) >= self._capacity:
            start = perf_counter()
            self._wait_one()
            self._stats['backpressure_seconds'] += perf_counter()-start
        # The worker owns these snapshots even if the producer reuses arrays.
        owned_args, owned_kwargs = deepcopy((args, kwargs))
        self._pending.append(self._executor.submit(self._spool.append, *owned_args, **owned_kwargs))
        self._stats['submitted'] += 1
        self._stats['max_pending'] = max(self._stats['max_pending'], len(self._pending))

    def finish(self, *args, **kwargs):
        if self.closed:
            raise RuntimeError('recorder is closed')
        start = perf_counter()
        try:
            if self._failure is not None:
                raise self._failure
            while self._pending:
                self._wait_one()
            self._stats['finish_wait_seconds'] = perf_counter()-start
            return self._spool.finish(*args, **kwargs)
        finally:
            # Also reap the thread on I/O errors. No ready marker on failure.
            self._executor.shutdown(wait=True, cancel_futures=True)
            self.closed = True
