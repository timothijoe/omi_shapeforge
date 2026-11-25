"""Own subprocess groups and persist native status before subsequent cleanup."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


class OwnedProcess:
    def __init__(self, command, *, directory, name, env=None, cwd=None):
        self.path = Path(directory) / (name + '_process.json')
        self.log = (Path(directory) / (name + '.log')).open('w')
        self.started = time.monotonic()
        self.record = dict(command=[str(x) for x in command], state='starting',
                           start_new_session=True, returncode=None)
        write_json(self.path, self.record)
        try:
            self.process = subprocess.Popen(command, env=env, cwd=cwd, stdout=self.log,
                stderr=subprocess.STDOUT, start_new_session=True)
        except BaseException as exc:
            self.record.update(state='spawn_failed', error=repr(exc))
            write_json(self.path, self.record); self.log.close()
            raise
        self.record.update(state='running', pid=self.process.pid, pgid=self.process.pid)
        write_json(self.path, self.record)

    def poll(self):
        code = self.process.poll()
        if code is not None and self.record['state'] != 'exited':
            self.record.update(state='exited', returncode=code,
                               elapsed_seconds=time.monotonic()-self.started)
            write_json(self.path, self.record)
            self.log.close()
        return code

    def wait(self, timeout):
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.record['timed_out'] = True
            write_json(self.path, self.record)
            self.stop()
            raise
        return self.poll()

    def stop(self):
        if self.poll() is not None:
            return
        self.record['stop_requested'] = True
        write_json(self.path, self.record)
        for sig, timeout in ((signal.SIGTERM, 10), (signal.SIGKILL, 10)):
            try:os.killpg(self.process.pid, sig)
            except ProcessLookupError:pass
            try:
                self.process.wait(timeout=timeout)
                break
            except subprocess.TimeoutExpired:continue
        self.poll()
