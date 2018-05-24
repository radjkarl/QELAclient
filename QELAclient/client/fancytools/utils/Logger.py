# -*- coding: utf-8 -*-
from time import localtime, strftime
import platform
import sys


class Logger(object):
    """
    writes into log-file and on screen at the same time

    >>> import sys
    >>> import os
    >>> logger = Logger(sys.stdout, 'my_logfile.log')
    >>> sys.stdout = logger
    >>> sys.stderr = logger

    every output will also be saved in file, e.g.
    >>> print('hello world') #every output will also be saved in file
    hello world

    to prove this we read the log file
    >>> logger.close()
    >>> log_file = open('my_logfile.log', 'r')

    >>> logcontent = log_file.read()
    >>> 'hello world' in logcontent
    True
    >>> os.remove('my_logfile.log')
    """

    def __init__(self, stdout, path, mode='w'):
        self.stdout = stdout
        self.logfile = open(path, mode)
        self.logfile.write('''\
####################################
New run at %s
%s
%s
####################################

''' % (strftime("%d.%m.%Y|%H:%M:%S", localtime()),
            platform.uname(), sys.version))

    def write(self, text):
        self.stdout.write(text)
        self.logfile.write(text)  # .encode('utf8'))
        self.logfile.flush()

    def close(self):
        # NEEDED??
        self.stdout.close()
        self.logfile.close()

    def flush(self):  # needed - .flush is called after exception
        pass


class MaxNLogger(Logger):
    '''
    generate a new file with current timestamp 
    once number of prints exceeds [maxN]
    '''

    def __init__(self, stdout, path, mode='w', maxN=10000,):
        self._n = 0
        self._maxN = maxN
        self.path = path
        Logger.__init__(self, stdout, self.getPath(), mode)

    def getPath(self):
        stamp = strftime("%Y_%m_%d__%H_%M_%S", localtime())
        ss = self.path.split('.')
        path = '.'.join(ss[:-1])
        typ = ss[-1]
        return '%s_%s.%s' % (path, stamp, typ)

    def write(self, text):
        self._n += 1
        if self._n == self._maxN:
            self.logfile.close()
            self.logfile = open(self.getPath(), 'w')
        Logger.write(self, text)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
