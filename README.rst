Basic inter-process locks
=========================

The exclusive_control package provides a basic portable implementation of
interprocess locks using lock files.  It it a fork of zc.lockfile.

The purpose if not specifically to lock files, but to simply provide locks
with an implementation based on file-locking primitives.  Of course, these
locks could be used to mediate access to *other* files.  For example, the
ZODB file storage implementation uses file locks to mediate access to
file-storage database files.  The database files and lock file files
are separate files.

Original author is: Zope Foundation and Contributors
