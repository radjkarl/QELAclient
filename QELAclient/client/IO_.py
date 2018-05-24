from fancytools.os.PathStr import PathStr
from datetime import datetime

hirarchy = ['Module', 'Number', 'Name', 'Current', ' Measurement Date']


def pathSplit(path):
    names = PathStr.splitNames(path)
    if len(names) == 4:
        mod = names[0]
        rest = names[3:]

        number, name = names[1].split('__')
        current, date = names[2].split('__')
        
        # 2016-10-04T11_06_45 -> 04/10/16 11:06:45
        # TODO: return localized result 
        date = datetime.strptime(date, "%Y-%m-%dT%H_%M_%S").strftime('%x %X')

        names = [mod, number, name, current, date]
        names.extend(rest)
    return names


def pathJoin(pathlist):
    if len(pathlist) > 5:
        mod, number, name, current, date = pathlist[:5]
#         date = date.replace(':', '-')
        date = datetime.strptime(date, '%x %X').strftime("%Y-%m-%dT%H_%M_%S")
        
        dd0 = '__'.join((number, name))
        dd1 = '__'.join((current, date))

        out = PathStr(mod).join(dd0, dd1)
        if len(pathlist[5:]):
            out = out.join(*tuple(pathlist[5:]))
        return out
    return PathStr(pathlist[0]).join(*pathlist[1:])
