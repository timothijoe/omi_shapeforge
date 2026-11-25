import threading
import unittest
from pathlib import Path

from omi_shapeforge.sim.async_episode_spool import AsyncEpisodeSpool


class Spool:
    directory = Path('/unused')

    def __init__(self, gate=None, entered=None, fail=False):
        self.records = []
        self.count = 0
        self.published = False
        self.gate, self.entered, self.fail = gate, entered, fail

    def append(self, value):
        if self.entered:self.entered.set()
        if self.gate and not self.gate.wait(5):raise TimeoutError('test gate')
        if self.fail:raise OSError('simulated disk failure')
        self.records.append(value);self.count += 1

    def finish(self, keep):
        self.published = keep
        return self.count


class AsyncEpisodeSpoolTests(unittest.TestCase):
    def test_snapshots_preserve_order_and_finish_waits_before_publication(self):
        gate = threading.Event();entered = threading.Event()
        inner = Spool(gate, entered);recorder = AsyncEpisodeSpool(inner)
        finishing = threading.Event();finished = threading.Event();outcomes = []
        def finish():
            finishing.set()
            try:outcomes.append(recorder.finish(True))
            except BaseException as exc:outcomes.append(exc)
            finally:finished.set()
        thread = threading.Thread(target=finish)
        try:
            value = {'frame':[1, 2], 'audit':{'step':0}}
            recorder.append(value)
            self.assertTrue(entered.wait(2))
            value['frame'][0] = 999;value['audit']['step'] = 999
            recorder.append({'frame':[3, 4], 'audit':{'step':1}})
            thread.start();self.assertTrue(finishing.wait(2))
            self.assertFalse(finished.wait(.05))
            self.assertFalse(inner.published)
            gate.set()
            thread.join(2);self.assertFalse(thread.is_alive())
            self.assertEqual(outcomes, [2])
            self.assertEqual(inner.records, [{'frame':[1,2], 'audit':{'step':0}}, {'frame':[3,4], 'audit':{'step':1}}])
            self.assertTrue(inner.published)
            self.assertEqual(recorder.statistics['submitted'], recorder.statistics['written'])
            self.assertTrue(recorder.closed)
        finally:
            gate.set()
            if thread.ident:thread.join(2)
            if not recorder.closed:recorder.finish(False)

    def test_full_queue_blocks_without_dropping_records(self):
        gate = threading.Event();entered = threading.Event();submitted = threading.Event();attempting = threading.Event();errors = []
        inner = Spool(gate, entered);recorder = AsyncEpisodeSpool(inner, max_pending=1)
        def submit():
            attempting.set()
            try:recorder.append(2);submitted.set()
            except BaseException as exc:errors.append(exc)
        thread = threading.Thread(target=submit)
        try:
            recorder.append(1);self.assertTrue(entered.wait(2));thread.start()
            self.assertTrue(attempting.wait(2))
            self.assertFalse(submitted.wait(.05))
            gate.set();thread.join(2)
            self.assertFalse(thread.is_alive());self.assertFalse(errors)
            recorder.finish(True)
            self.assertEqual(inner.records, [1,2])
            self.assertEqual(recorder.statistics['max_pending'], 1)
            self.assertGreater(recorder.statistics['backpressure_seconds'], 0)
        finally:
            gate.set()
            if thread.ident:thread.join(2)
            if not recorder.closed:recorder.finish(False)

    def test_io_failure_propagates_and_never_publishes_ready(self):
        inner = Spool(fail=True);recorder = AsyncEpisodeSpool(inner)
        recorder.append(1)
        with self.assertRaisesRegex(OSError, 'disk failure'):recorder.finish(True)
        self.assertFalse(inner.published);self.assertTrue(recorder.closed)
        with self.assertRaises(RuntimeError):recorder.append(2)

    def test_invalid_capacity_is_rejected_before_starting_thread(self):
        for size in (0, -1, 1.5, True):
            with self.assertRaises(ValueError):AsyncEpisodeSpool(Spool(), max_pending=size)


if __name__ == '__main__':unittest.main()
