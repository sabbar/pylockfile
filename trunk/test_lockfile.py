import os
import threading

from lockfile import *

class ComplianceTest(object):
    def setup(self):
        global FileLock
        self.saved_class = FileLock
        FileLock = self.class_to_test

    def teardown(self):
        global FileLock
        FileLock = self.saved_class

    def test_acquire(self):
        # As simple as it gets.
        lock = FileLock(_testfile())
        lock.acquire()
        assert lock.is_locked()
        lock.release()
        assert not lock.is_locked()

        # No timeout test
        e1, e2 = threading.Event(), threading.Event()
        t = _in_thread(_lock_wait_unlock, e1, e2)
        e1.wait()         # wait for thread t to acquire lock
        lock2 = FileLock(_testfile())
        assert lock2.is_locked()
        assert not lock2.i_am_locking()

        try:
            lock2.acquire(timeout=-1)
        except AlreadyLocked:
            pass
        else:
            lock2.release()
            raise AssertionError, ("did not raise AlreadyLocked in thread %s" %
                                   threading.currentThread().getName())

        e2.set()          # tell thread t to release lock
        t.join()

        # Timeout test
        e1, e2 = threading.Event(), threading.Event()
        t = _in_thread(_lock_wait_unlock, e1, e2)
        e1.wait()                        # wait for thread t to acquire filelock
        lock2 = FileLock(_testfile())
        assert lock2.is_locked()
        try:
            lock2.acquire(timeout=0.1)
        except LockTimeout:
            pass
        else:
            lock2.release()
            raise AssertionError, ("did not raise LockTimeout in thread %s" %
                                   threading.currentThread().getName())

        e2.set()
        t.join()

    def test_release(self):
        lock = FileLock(_testfile())
        lock.acquire()
        assert lock.is_locked()
        lock.release()
        assert not lock.is_locked()
        assert not lock.i_am_locking()
        try:
            lock.release()
        except NotLocked:
            pass
        except NotMyLock:
            raise AssertionError, 'unexpected exception: %s' % NotMyLock
        else:
            raise AssertionError, 'erroneously unlocked file'

        e1, e2 = threading.Event(), threading.Event()
        t = _in_thread(_lock_wait_unlock, e1, e2)
        e1.wait()
        lock2 = FileLock(_testfile())
        assert lock2.is_locked()
        assert not lock2.i_am_locking()
        try:
            lock2.release()
        except NotMyLock:
            pass
        else:
            raise AssertionError, ('erroneously unlocked a file locked'
                                   ' by another thread.')
        e2.set()
        t.join()

    def test_is_locked(self):
        lock = FileLock(_testfile())
        lock.acquire()
        assert lock.is_locked()
        lock.release()
        assert not lock.is_locked()

    def test_i_am_locking(self):
        lock1 = FileLock(_testfile(), threaded=False)
        lock1.acquire()
        assert lock1.is_locked()
        lock2 = FileLock(_testfile())
        assert lock1.i_am_locking()
        assert not lock2.i_am_locking()
        try:
            lock2.acquire(timeout=2)
        except LockTimeout:
            lock2.break_lock()
            assert not lock2.is_locked()
            assert not lock1.is_locked()
            lock2.acquire()
        else:
            raise AssertionError('expected LockTimeout...')
        assert not lock1.i_am_locking()
        assert lock2.i_am_locking()
        lock2.release()

    def test_break_lock(self):
        lock = FileLock(_testfile())
        lock.acquire()
        assert lock.is_locked()
        lock2 = FileLock(_testfile())
        assert lock2.is_locked()
        lock2.break_lock()
        assert not lock2.is_locked()
        try:
            lock.release()
        except NotLocked:
            pass
        else:
            raise AssertionError('break lock failed')

    def test_enter(self):
        lock = FileLock(_testfile())
        with lock:
            assert lock.is_locked()
        assert not lock.is_locked()

def _in_thread(func, *args, **kwargs):
    """Execute func(*args, **kwargs) after dt seconds. Helper for tests."""
    def _f():
        func(*args, **kwargs)
    t = threading.Thread(target=_f, name='/*/*')
    t.start()
    return t

def _testfile():
    """Return platform-appropriate file.  Helper for tests."""
    import tempfile
    return os.path.join(tempfile.gettempdir(), 'trash-%s' % os.getpid())

def _lock_wait_unlock(event1, event2):
    """Lock from another thread.  Helper for tests."""
    with FileLock(_testfile()):
        event1.set()  # we're in,
        event2.wait() # wait for boss's permission to leave

class TestLinkFileLock(ComplianceTest):
    class_to_test = LinkFileLock

class TestMkdirFileLock(ComplianceTest):
    class_to_test = MkdirFileLock

try:
    import sqlite3
except ImportError:
    pass
else:
    class TestSQLiteFileLock(ComplianceTest):
        class_to_test = SQLiteFileLock
