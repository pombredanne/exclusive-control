##############################################################################
#
# Copyright (c) 2004 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
import doctest
import os
import re
import sys
import tempfile
import threading
import time
import unittest

import exclusive_control

from unittest.mock import Mock, patch
import shutil

def inc():
    while 1:
        try:
            lock = exclusive_control.LockFile('f.lock')
        except exclusive_control.LockError:
            continue
        else:
            break
    f = open('f', 'r+b')
    v = int(f.readline().strip())
    time.sleep(0.01)
    v += 1
    f.seek(0)
    f.write(('%d\n' % v).encode('ASCII'))
    f.close()
    lock.close()


def many_threads_read_and_write():
    r"""
    >>> with open('f', 'w+b') as file:
    ...     _ = file.write(b'0\n')
    >>> with open('f.lock', 'w+b') as file:
    ...     _ = file.write(b'0\n')

    >>> n = 50
    >>> threads = [threading.Thread(target=inc) for i in range(n)]
    >>> _ = [thread.start() for thread in threads]
    >>> _ = [thread.join() for thread in threads]
    >>> with open('f', 'rb') as file:
    ...     saved = int(file.read().strip())
    >>> saved == n
    True

    >>> os.remove('f')

    We should only have one pid in the lock file:

    >>> f = open('f.lock')
    >>> len(f.read().strip().split())
    1
    >>> f.close()

    >>> os.remove('f.lock')

    """


def pid_in_lockfile():
    r"""
    >>> import os, exclusive_control
    >>> pid = os.getpid()
    >>> lock = exclusive_control.LockFile("f.lock")
    >>> f = open("f.lock")
    >>> _ = f.seek(1)
    >>> f.read().strip() == str(pid)
    True
    >>> f.close()

    Make sure that locking twice does not overwrite the old pid:

    >>> lock = exclusive_control.LockFile("f.lock")
    Traceback (most recent call last):
      ...
    LockError: Couldn't lock 'f.lock'

    >>> f = open("f.lock")
    >>> _ = f.seek(1)
    >>> f.read().strip() == str(pid)
    True
    >>> f.close()

    >>> lock.close()
    """


def hostname_in_lockfile():
    r"""
    hostname is correctly written into the lock file when it's included in the
    lock file content template

    >>> import exclusive_control
    >>> with patch('socket.gethostname', Mock(return_value='myhostname')):
    ...     lock = exclusive_control.LockFile("f.lock", content_template='{hostname}')
    >>> f = open("f.lock")
    >>> _ = f.seek(1)
    >>> f.read().rstrip()
    'myhostname'
    >>> f.close()

    Make sure that locking twice does not overwrite the old hostname:

    >>> lock = exclusive_control.LockFile("f.lock", content_template='{hostname}')
    Traceback (most recent call last):
      ...
    LockError: Couldn't lock 'f.lock'

    >>> f = open("f.lock")
    >>> _ = f.seek(1)
    >>> f.read().rstrip()
    'myhostname'
    >>> f.close()

    >>> lock.close()
    """


class TestLogger(object):

    def __init__(self):
        self.log_entries = []

    def exception(self, msg, *args):
        self.log_entries.append((msg,) + args)


class LockFileLogEntryTestCase(unittest.TestCase):
    """Tests for logging in case of lock failure"""

    def setUp(self):
        self.here = os.getcwd()
        self.tmp = tempfile.mkdtemp(prefix='exclusive_control-test-')
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self.here)
        shutil.rmtree(self.tmp)

    def test_log_entry(self):
        # PID and hostname are parsed and logged from lock file on failure
        test_logger = TestLogger()

        def lock(locked, before_closing):
            lock = None
            try:
                lock = exclusive_control.LockFile('f.lock',
                                            content_template='{pid}/{hostname}')
            except Exception:
                pass
            locked.set()
            before_closing.wait()
            if lock is not None:
                lock.close()

        with patch('os.getpid', Mock(return_value=123)):
            with patch('socket.gethostname', Mock(return_value='myhostname')):
                with patch.object(exclusive_control, 'logger', test_logger):
                    first_locked = threading.Event()
                    second_locked = threading.Event()
                    thread1 = threading.Thread(
                        target=lock, args=(first_locked, second_locked))
                    thread2 = threading.Thread(
                        target=lock, args=(second_locked, second_locked))
                    thread1.start()
                    first_locked.wait()
                    assert not test_logger.log_entries
                    thread2.start()
                    thread1.join()
                    thread2.join()
        expected = [('Error locking file %s; content: "%s%s"',
                     'f.lock', '123/myhostname', '')]
        assert test_logger.log_entries == expected, test_logger.log_entries

    def test_unlock_and_lock_while_multiprocessing_process_running(self):
        import multiprocessing

        lock = exclusive_control.LockFile('l')
        q = multiprocessing.Queue()
        p = multiprocessing.Process(target=q.get)
        p.daemon = True
        p.start()

        # release and re-acquire should work (obviously)
        lock.close()
        lock = exclusive_control.LockFile('l')
        self.assertTrue(p.is_alive())

        q.put(0)
        lock.close()
        p.join()


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocFileSuite('README.txt')
    # Add unittest test cases from this module
    suite.addTest(unittest.defaultTestLoader.loadTestsFromName(__name__))
    return suite