"""Starts a program in its own process and streams its output."""

import codecs
import os
import queue
import subprocess
import sys
import threading

from .paths import FROZEN, LAUNCHER, NO_WINDOW


def child_command():
    """The command that runs a translated Python file: the IDE itself, in 'run' mode (see plain_ide.py)."""
    return [sys.executable, "--run"] if FROZEN else [sys.executable, LAUNCHER, "--run"]


class Runner:
    def __init__(self):
        self.proc = None
        self.events = queue.Queue()

    @property
    def running(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self, cmd, extra_env=None):
        env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8", **(extra_env or {}))
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, bufsize=0, env=env,
                                     creationflags=NO_WINDOW)
        threading.Thread(target=self._pump, args=(self.proc,), daemon=True).start()

    def _pump(self, proc):
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        while True:
            try:
                data = os.read(proc.stdout.fileno(), 4096)
            except OSError:
                break
            if not data:
                break
            self.events.put((proc, "out", decoder.decode(data).replace("\r", "")))
        self.events.put((proc, "exit", proc.wait()))

    def send(self, line):
        try:
            self.proc.stdin.write((line + "\n").encode("utf-8"))
            self.proc.stdin.flush()
        except (OSError, ValueError, AttributeError):
            pass

    def stop(self):
        if self.running:
            self.proc.kill()
