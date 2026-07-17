import os
import time
import tempfile

# Simple PID file lock for cross-process exclusive access to the OAK device.
# The lock file lives in the OS temp dir (portable across Linux/Windows) and
# stores the PID of the owning process. acquire_lock will try to create the
# lock atomically and optionally wait for a timeout. release_lock removes the
# lock if owned. Re-acquiring from the SAME process is a no-op (reentrant), so
# the camera-recovery path can re-init without deadlocking on its own lock.

LOCK_PATH = os.path.join(tempfile.gettempdir(), 'oak_camera.pid')


def _read_pid(path):
    try:
        with open(path, 'r') as f:
            return int(f.read().strip())
    except Exception:
        return None


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


def acquire_lock(timeout=5.0, poll_interval=0.2):
    """Try to atomically acquire the lock. Returns True if acquired.

    If existing lock PID is dead, it will be removed and lock retried.
    """
    start = time.time()
    while True:
        # Reentrant: if we already own the lock, treat it as acquired.
        existing = _read_pid(LOCK_PATH)
        if existing is not None and existing == os.getpid():
            return True
        # Try to create the file atomically using O_CREAT|O_EXCL
        try:
            fd = os.open(LOCK_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            with os.fdopen(fd, 'w') as f:
                f.write(str(os.getpid()))
            return True
        except FileExistsError:
            # Read existing pid
            existing = _read_pid(LOCK_PATH)
            if existing is None:
                # Corrupt file - remove and retry
                try:
                    os.remove(LOCK_PATH)
                except Exception:
                    pass
            else:
                if not _pid_alive(existing):
                    # Stale lock - remove and retry
                    try:
                        os.remove(LOCK_PATH)
                    except Exception:
                        pass
                else:
                    # Still alive; wait
                    if timeout is not None and (time.time() - start) >= timeout:
                        return False
                    time.sleep(poll_interval)
                    continue
        except Exception:
            # Unexpected error - fail safe
            return False


def release_lock():
    try:
        if os.path.exists(LOCK_PATH):
            pid = _read_pid(LOCK_PATH)
            if pid == os.getpid():
                os.remove(LOCK_PATH)
                return True
    except Exception:
        pass
    return False

def get_lock_owner():
    """Return the PID recorded in the lock file, or None if not present/corrupt."""
    return _read_pid(LOCK_PATH)
