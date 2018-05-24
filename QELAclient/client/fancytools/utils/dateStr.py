
from datetime import datetime
import time


def dateStr(timestamp=None):
    ''' 1515646018.0 -> '01/11/18 12:46:58' '''
    if timestamp is None:
        timestamp = time.time()
    return datetime.fromtimestamp(timestamp).strftime('%x %X')
    # '%Y-%m-%d %H:%M:%S'


def strDate(s):
    ''' '01/11/18 12:46:58' -> 1515646018.0'''
    return time.mktime(time.strptime(s, "%x %X"))

# def gmtimeStr():
#     return time.strftime("%x %X", time.gmtime())


if __name__ == '__main__':
    print(dateStr(1517902087))
