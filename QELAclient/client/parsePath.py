import re
from datetime import datetime

# def _numberAndName(row, index):
#     ind = 1
#     for ind, c in enumerate(index):
#         if not c.isdigit():
#             break
#     row[1] = index[ind:]  # measurement name
#     try:  # meas. number
#         row[0] = int(index[:ind])
#     except (ValueError, UnboundLocalError):
#         row[0] = 1


def _current(row, basename):
    try:
        end = basename.index('A')
        for i in range(end - 1, -1, -1):
            if not basename[i].isdigit() and basename[i] != '-':
                break
        rr = basename[i:end].replace('-', '.')

        row[2] = float(rr)
    except Exception:
        # background?
        row[2] = 0


def _name(row, s):
    row[0] = s


def _ID(row, s):
    row[1] = s


# format functions:
def _onlyDigits(s):
    s = re.sub('[^\d\.]', "", s)  # filter digits and dots
    if s[-1] == '.':
        s = s[:-1]
    return s


def _int(s):
    return int(_onlyDigits(s))


def _float(s):
    return float(_onlyDigits(s))


def _time(row, s):
    row[3] = _float(s)


def _pass(s):
    return s


def _date(style, s):
#     return datetime.strptime(s, style).strftime('%x %X')
#     return datetime.strptime("2016/01/01 12:00:05", "%Y/%m/%d %H:%M:%S").isoformat()
    return datetime.strptime(s, style).isoformat()


CAT_FUNCTIONS = {'Measurement':_name,  # "Meas. number and name [##Name]": _numberAndName,
                 'Current [#A]': _current,
                 'Module ID': _ID,
                 'Exposure time [#s]': _time}

# format function TabUpload table columns
_DD = {  # 'n': _int,  # meas number
       'N': _pass,  # meas name
       'i': _pass,  # ID
       'C': _float,  # current
       'D': _date,  # date
       't': _float,  # exposure time
       'I': _float,  # iso
       'f': _float}  # fnumber

# column index in TabUpload table:
_RR = {  # 'n': 0,  # meas number
       'N': 0,  # meas name
       'i': 1,  # ID
       'C': 2,  # current
       'D': 3,  # date
       't': 4,  # exposure time
       'I': 5,  # iso
       'f': 6}


def toRow(row, d):
    for k, v in d.items():
        row[_RR[k]] = v


def parsePath(path, style):  #    #n --> Measurement index 
    '''
    Extract values such as ISO, exposure time etc from directory of file name.
    Values to be extracted are indicated with a leading '%' followed be a value code:
    #N --> Measurement name
    #i --> Module ID
    #C --> Current [A]
    #D{...} --> Date, format following https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
              example:
              #D{%Y-%m-%d_%H:%M} --> 2018-12-02_15:34
    #t --> exposure time [s]
    #I --> ISO
    #f --> f-number
    '''
    out = {}  # X:val
    while True:
        try:
            # start index
            i0 = style.index('#')
            j0 = i0
        except ValueError:
            break

        styp = style[i0 + 1]  # n,N,T...

        typ = _DD.get(styp, _pass)  # _float, _int...

        if typ == _date:  # extract datetype the str between {}
            i = i0 + 2
            iend = style[i + 2:].index('}') + i
            datetype = style[i + 1:iend + 2]
            i0 = iend + 1

        try:  # stop index
            nextletter = style[i0 + 2]
            i1 = i0 + 2
            j1 = j0 + path[j0:].index(nextletter, None)
        except (ValueError, IndexError):
            i1, j1 = None, None

        # get value
        sval = path[j0:j1]
        if typ == _date:
            val = _date(datetype, sval)
        else:
            val = typ(sval)
        out[styp] = val
        if i1 is None:
            break
        # shorten style and path:
        path = path[j1:]
        style = style[i1:]

    return out


if __name__ == '__main__':
    D = [
        # PATH          STYLE        ANSWER
        (r'03rd Round', '0#nrd #N', {'n': 3, 'N': 'Round'}),
        # PATH
         (r'12__33_AA-2.3_XXX_2015-02-24T13:00:00.png',
          # STYLE
          '#n__#t_AA-#f_XXX_#D{%Y-%m-%dT%H:%M:%S}.png',
          # ANSWER
          {'n': 12, 't': 33.0, 'f': 2.3, 'D': '2015-02-24T13:00:00'})
         ]

    for path, style, answer in D:
        assert parsePath(path, style) == answer, '%s != %s' % (parsePath(path, style) , answer)
