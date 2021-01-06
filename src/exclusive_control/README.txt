Lock file support
=================

The exclusive_control module provides support for creating file system
locks.  These are locks that are implemented with lock files and
OS-provided locking facilities. 
It is based on the fork and merge of ZODB zc.lockfile and yg.lockfile
libraries in a single library.

To create a lock, instantiate a
LockFile object with a file name:

    >>> import exclusive_control
    >>> lock = exclusive_control.LockFile('lock')

If we try to lock the same name, we'll get a lock error:

    >>> try:
    ...     exclusive_control.LockFile('lock')
    ... except exclusive_control.LockError:
    ...     print("Can't lock file")
    Can't lock file

    >>> for record in handler.records: # doctest: +ELLIPSIS
    ...     print(record.levelname+' '+record.getMessage())
    ERROR Error locking file lock; pid=...

To release the lock, use it's close method:

    >>> lock.close()

The lock file is not removed.  It is left behind:

    >>> import os
    >>> os.path.exists('lock')
    True

Of course, now that we've released the lock, we can create it again:

    >>> lock = exclusive_control.LockFile('lock')
    >>> lock.close()

.. Cleanup

    >>> import os
    >>> os.remove('lock')

Hostname in lock file
=====================

In a container environment (e.g. Docker), the PID is typically always
identical even if multiple containers are running under the same operating
system instance.

Clearly, inspecting lock files doesn't then help much in debugging. To identify
the container which created the lock file, we need information about the
container in the lock file. Since Docker uses the container identifier or name
as the hostname, this information can be stored in the lock file in addition to
or instead of the PID.

Use the ``content_template`` keyword argument to ``LockFile`` to specify a
custom lock file content format:

    >>> lock = exclusive_control.LockFile('lock', content_template='{pid};{hostname}')
    >>> lock.close()

If you now inspected the lock file, you would see e.g.:

    $ cat lock
     123;myhostname

