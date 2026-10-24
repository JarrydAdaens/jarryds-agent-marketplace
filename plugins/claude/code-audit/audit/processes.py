"""Serial, bounded, run-owned subprocesses; no shell, downloads, or name-based kills."""
import ctypes
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

from .common import AuditError, atomic, now


class WindowsJob:
    """Gate the child until assignment; kill-on-close includes scanner descendants."""
    def __init__(self, process, memory_mb):
        from ctypes import wintypes as w
        class Basic(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64),
                        ('flags', w.DWORD), ('min_ws', ctypes.c_size_t), ('max_ws', ctypes.c_size_t),
                        ('active', w.DWORD), ('affinity', ctypes.c_size_t),
                        ('priority', w.DWORD), ('scheduling', w.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in ('ro', 'wo', 'oo', 'rt', 'wt', 'ot')]
        class Extended(ctypes.Structure):
            _fields_ = [('basic', Basic), ('io', IO), ('process_memory', ctypes.c_size_t),
                        ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t),
                        ('peak_job', ctypes.c_size_t)]
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
        self.api.CreateJobObjectW.restype = w.HANDLE
        self.api.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
        self.api.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        self.api.CloseHandle.argtypes = [w.HANDLE]
        self.handle = self.api.CreateJobObjectW(None, None)
        limits = Extended()
        limits.basic.flags = 0x2000 | 0x200  # KILL_ON_JOB_CLOSE | JOB_MEMORY
        limits.job_memory = int(memory_mb * 1024 * 1024)
        if not self.handle or not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            self.close()
            raise AuditError('Windows Job Object containment unavailable')
        if not self.api.AssignProcessToJobObject(self.handle, w.HANDLE(int(process._handle))):
            self.close()
            raise AuditError('Cannot assign owned scanner launcher to Windows job')

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


def execute(command, cwd, folder, timeout, memory_mb=4096, min_disk_mb=256, cancel_file=None):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(folder).free < min_disk_mb * 1024 * 1024:
        raise AuditError('Insufficient disk headroom')
    if not command or not isinstance(command, list) or any(not isinstance(x, str) for x in command):
        raise AuditError('Executable argv must be a nonempty string array')
    env = {k: v for k, v in os.environ.items() if k.upper() in
           {'PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'PATHEXT', 'LANG', 'LC_ALL'}}
    env.update(GIT_TERMINAL_PROMPT='0', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
    job, process = None, None
    started = time.monotonic()
    info = {'started': now(), 'command': command, 'cwd': str(cwd), 'pid': None,
            'containment': 'windows-job' if os.name == 'nt' else 'process-group',
            'timeout_seconds': timeout, 'memory_limit_mb': memory_mb}
    with (folder / 'stdout.txt').open('wb') as out, (folder / 'stderr.txt').open('wb') as err:
        try:
            if os.name == 'nt':
                # No scanner starts before job assignment succeeds.
                gate = 'import json,subprocess,sys; a=json.loads(sys.stdin.readline()); sys.exit(subprocess.call(a))'
                process = subprocess.Popen([sys.executable, '-c', gate], cwd=cwd, env=env,
                                           stdin=subprocess.PIPE, stdout=out, stderr=err,
                                           creationflags=subprocess.CREATE_NO_WINDOW)
                job = WindowsJob(process, memory_mb)
                process.stdin.write((json.dumps(command) + '\n').encode())
                process.stdin.close()
            else:
                def limit():
                    import resource
                    resource.setrlimit(resource.RLIMIT_AS, (int(memory_mb * 1024**2),) * 2)
                process = subprocess.Popen(command, cwd=cwd, env=env, stdout=out, stderr=err,
                                           start_new_session=True, preexec_fn=limit)
            info['pid'] = process.pid
            atomic(folder / 'process.json', info)
            while True:
                if cancel_file and Path(cancel_file).exists():
                    info.update(exit_code=None, timed_out=False, cancelled=True)
                    break
                remaining = timeout - (time.monotonic() - started)
                if remaining <= 0:
                    info.update(exit_code=None, timed_out=True)
                    break
                try:
                    code = process.wait(timeout=min(0.2, remaining))
                    info.update(exit_code=code, timed_out=False, cancelled=False)
                    break
                except subprocess.TimeoutExpired:
                    pass
        finally:
            if job:
                job.close()
            elif process and os.name != 'nt':
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if process:
                if process.poll() is None:
                    process.kill()
                process.wait()
            info.update(ended=now(), elapsed_seconds=round(time.monotonic() - started, 4))
            atomic(folder / 'process.json', info)
    return info
