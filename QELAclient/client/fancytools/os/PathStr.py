# -*- coding: utf-8 -*-
import os
import shutil
import sys


class PathStr(str):
    """
    easy path-string handling and manipulation using os.path and shutil

    Windows only: only pass raw strings, like r'c:\...' 
                  in order to not confuse python

    >>> p = PathStr.home()
    >>> print (p.isdir())
    True
    >>> print (p.exists())
    True
    >>> d_list = [p.join(x) for x in p.listdir()]
    ...
    """

    def __new__(cls, value):
        """transform raw-string and / to \ depending on the os"""
        obj = str.__new__(cls, os.path.normpath(str(value)))
        return obj

    @staticmethod
    def home():
        """return the home/user directory"""
        return PathStr(os.path.expanduser("~"))

    def splitNames(self):
        '''
        split path into all directory and file names:
        /PATH/TO/FILE.xyz --> [PATH, TO, FILE.xyz]
        '''
        ll = []
        p = self
        while True:
            p, end = os.path.split(p)
            if not len(p) or not len(end):
                if p:
                    ll.append(p)
                if end:
                    ll.append(end)
                break
            ll.append(end)
        ll.reverse()
        return ll

    def rmFileType(self):
        '''
        Remove file type from path:
        /myFile.xyz --> myFile.xyz
        /.myFile.xyz --> /.myFile
        '''
        try:
            ind = self[::-1].index('.')
            if self[-ind - 2] in ('\\', '//'):  # is hidden folder or files without ftype
                return self
            return self[:-ind - 1]
        except IndexError:
            return self
#         return '.'.join(self.split('.')[:-1])

    def date(self):
        return os.stat(self).st_mtime

    def size(self):
        '''
        file/directory size in bytes
        '''
        if self.isdir():

            def folder_size(path):
                total = 0
                for entry in os.scandir(path):
                    if entry.is_file():
                        total += entry.stat().st_size
                    elif entry.is_dir():
                        total += folder_size(entry.path)
                return total

            return folder_size(self)
        return os.stat(self).st_size

    def raw(self):
        """Try to transform str to raw str"
        ... this will not work every time
        """
        escape_dict = {'\a': r'\a',
                       '\b': r'\b',
                       '\c': r'\c',
                       '\f': r'\f',
                       '\n': r'\n',
                       '\r': r'\r',
                       '\t': r'\t',
                       '\v': r'\v',
                       # '\x':r'\x',#cannot do \x - otherwise exception
                       '\'': r'\'',
                       '\"': r'\"',
                       # '\0':r'\0', #doesnt work
                       '\1': r'\1',
                       '\2': r'\2',
                       '\3': r'\3',
                       '\4': r'\4',
                       '\5': r'\5',
                       '\6': r'\6',
                       # '\7':r'\7',#same as \a is ASCI
                       }

        new_string = ''
        for char in self:
            try:
                new_string += escape_dict[char]
            except KeyError:
                new_string += char
        return new_string

    @staticmethod
    def getcwd(moduleName=None):
        """
        get current path either from the temp folder used by pyinstaller:

            * apps 'sys._MEIPASS' if packed with --onefile option

        or

            * os.getcwd()
        """
        try:
            p = PathStr(sys._MEIPASS)
            if moduleName is not None:
                # pyinstaller create one temp folder
                # to separate e.g. media directories from each package it is useful
                # to build its file-tree like this /temp/[mainPackage]/
                # to get the main package PathStr need a derived instance
                return p.join(moduleName.split('.')[0])
            return p
        except AttributeError:
            return PathStr(os.getcwd())

    def join(self, *args):
        """add a file/name to this PathStr instance"""
        return PathStr(os.path.join(self, *args))

    def savejoin(self, *args):
        '''
        like .join() doe not allow parent/root folder selection 
        e.g.
        
        >>> P = =  PathStr('C:\\Users\\me\\Documents')
        >>> print(P.join('..', 'secret'))
        C:\\Users\\me\\secret
        
        >>> print(P.savejoin('..', 'secret'))
        C:\\Users\\me\\Documents\\secret
        '''
        args2 = []
        for a in args:
            if len(a):
                if a[0] in ('\\', '/'):
                    a = a[1:]
                a = a.replace('..', '')
                args2.append(a)
        return self.join(*args2)

    def exists(self):
        """return whether PathStr instance exists as a file/folder"""
        return os.path.exists(self)

    def abspath(self):
        return PathStr.join(PathStr.getcwd(), self)

    def load(self, size):
        """open and read the file is existent"""
        if self.exists() and self.isfile():
            return eval(open(self).read(size))

    def dirname(self):
        return PathStr(os.path.dirname(self))

    def basename(self):
        return PathStr(os.path.basename(self))

    def move(self, dst, forceoverride=False):
        """move this file/folder the [dst]"""
        d = PathStr(dst).join(self.basename())
        if forceoverride and d.exists():
            d.remove()
        shutil.move(self, dst)
        return d

    def copy(self, dst):
        dst = PathStr(dst)
        if self.isdir():
            #             try:
            shutil.copytree(self, dst)
#             except FileExistsError:
#                 shutil.copytree(self, dst.join(self.basename()))

        else:
            shutil.copy2(self, dst)
        return dst  # PathStr(dst)

    def mkdir(self, *dname):
        if not self.exists():
            os.mkdir(self)
        s = self
        for n in dname:
            s = s.join(n)
            if not s.exists():
                os.mkdir(s)
        return s

    def rename(self, new_file_name):
        newname = self.dirname().join(new_file_name)
        os.rename(self, newname)
        return newname

    def symlink(self, dst):
        '''
        of symlink() raises <OSError: symbolic link privilege not held>
        give user permission... 
        https://superuser.com/questions/104845/permission-to-make-symbolic-links-in-windows-7
        and update permissions:
             cme.exe >>> gpupdate /force
        '''
        try:
            os.symlink(self.abspath(), dst)
        except OSError as e:
            if str(e) == 'symbolic link privilege not held':
                raise OSError('''PathStr.symlink failed. Looks like you are lacking privilege to create symlinks. 
                Please check: https://stackoverflow.com/questions/6260149/os-symlink-support-in-windows?answertab=votes#tab-top''')
            raise

    def remove(self, name=None):
        f = self
        if name:
            f = self.join(name)
        if f.isdir():
            try:
                os.rmdir(f)
            except OSError:
                shutil.rmtree(f)
        else:
            os.remove(f)

    def filetype(self):
        if '.' in self:
            return self.split('.')[-1].lower()
        return ''

    def setFiletype(self, ftype):
        if '.' in self:
            s = self[:-self[::-1].index('.') - 1]
        else:
            s = self
        return PathStr(s + '.' + ftype)

    def extend(self, add):
        '''
        add <s> for path name:
            path = a/b/c.py  
            s='_1'
            -> a/b/c_1.py
        '''
        ss = self.split('.')
        s0 = '.'.join(ss[:-1])
        s1 = ss[-1]
        return '%s%s.%s' % (s0, add, s1) 

    def isfile(self):
        return os.path.isfile(self)

    def isdir(self):
        return os.path.isdir(self)

    def isFileLike(self):
        '''
        whether path would be a file (independent wether it exist or not
             True : .../jhg.hg  [file]
             False /jgu/jg      [dir]
             False  /jhg/.hg    [hidden] 
        '''
        return '.' in self.basename()[1:]

    def isHidden(self):
        return self.basename()[0] == '.'

    def listdir(self):
        if os.path.isdir(self):
            d = self
        else:
            d = os.path.dirname(self)
        return os.listdir(d)

# TODO: remove as soon an new files() is stable
#     def files(self, ftype=None):
#         """
#         return a first of path to all files within that folder
#         """
#         a = [self.join(i) for i in self]
#         if ftype is not None:
#             return [i for i in a if i.isfile() and i.filetype() == ftype]
#         return [i for i in a if i.isfile()]

    def files(self, ftype=None):
        """
        return a first of path to all files within that folder
        """
        for i in self:
            i = self.join(i)
            if i.isfile() and (ftype is None or i.filetype() == ftype):
                yield i

    def count(self, nested=True):
        '''count number of files'''
        if self.isdir():

            def _count(path):
                total = 0
                for entry in os.scandir(path):
                    if entry.is_file():
                        total += 1  # entry.stat().st_size
                    elif entry.is_dir() and nested:
                        total += _count(entry.path)
                return total

            return _count(self)
        return 1  # os.stat(self).st_size

    def nestedFiles(self, includeroot=True, maxdepth=100):
        '''
        returns list of all files in this and in all subfolders
        '''
#         ll = []

        def _fn(depth, p):
            for f in p:
                ff = p.join(f)
                if depth < maxdepth and ff.isdir():
                    yield from _fn(depth + 1, ff)
                else:
                    if not includeroot:
                        ff = PathStr(ff[len(self) + 1:])
                    yield ff

        yield from _fn(0, self)

    def folders(self):
        for i in self:
            i = self.join(i)
            if not i.isfile():
                yield i
#         a = [self.join(i) for i in self]
#         return [i for i in a if not i.isfile()]

    def star(self):
        '''
        substitute all '*' with all files/folders at that position
        !!! only single * expression supported at the moment

        >>> f = list(PathStr.home().join('*','image.png').star())
        ...

        output would then be ['D:\Measurements\mod1\one\image.png',
        ... 'D:\Measurements\mod1\two\image.png',
        ... ]
        '''
        assert self.count(
            "*") == 1, 'can only handle single star expressions at the moment'
        ff = self.split("*")
        ff0 = PathStr(ff[0])
        out = ff0.listdir()
        ff1 = PathStr(ff[1]).splitNames()[1:]
        for o in out:
            yield ff0.join(o, *ff1)

    def __iter__(self):
        # TODO: iter and listdir as generator object
        if self.exists():
            return iter(self.listdir())
        return iter([])

    def all(self):
        """
        Return a list of all files within this folder
        """
        return [self.join(i) for i in self]


if __name__ == "__main__":
    p = PathStr(r'C:\Users\karl\Documents\Work\Programming\git\daServer\data\users\karl2\calibration')
    print(p.join(r'\test'))

    jhh
    import doctest
    doctest.testmod()
