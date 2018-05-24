# i am building with py3.6 on  win10.
# to  also support win7,8, have to install:
# https://www.microsoft.com/en-US/download/details.aspx?id=48145
# see: https://github.com/pyinstaller/pyinstaller/blob/38721ef440344d416e26bbaa91a0acb23d0bf948/doc/usage.rst #platform specific notes
# installing this dependency is now embedded in  the installer :-)

import time
global pkg_dir
pkg_dir = os.path.dirname(os.path.abspath(os.curdir))

# intels math kernel library is huge 
# openblas is reasonably smaller
# since we dont need a fast numpy for the client,  lets rather generate a smaller exe:
# nuMKLnumber can be found at https://pypi.python.org/pypi/numpy 
# is can be installed in parallel to  an existing numpy via:
# pip  install numpy-1.14.2-cp36-none-win_amd64.whl --target <DORECTORY> --ignore-installed
import sys
sys.path.insert(0, os.path.abspath('noMKLnumpy'))



def relpath(loc, d):
    if not loc:
        return ''
    else:
        return d[d.index(r"\""[0] + loc) + 1:]


def addDataFiles():
    import os
    extraDatas = []
    dirs = [
        ('client', os.path.join(pkg_dir, 'qelaClient', 'QELAclient', 'client')),
    ]
    for loc, d in dirs:
        if os.path.isfile(d):
            extraDatas.append((relpath(loc, d), d, 'DATA'))
        else:
            for root, subFolders, files in os.walk(d):
                if not '__pycache__' in root: #exclude pyc files
                    for file in files:
                        r = os.path.join(root, file)
                        extraDatas.append((relpath(loc, r), r, 'DATA'))
    return extraDatas


a = Analysis(['QELAclient\\start.py'],
             pathex=[os.path.join(pkg_dir, f)
                     for f in os.listdir(pkg_dir)],

             hiddenimports=['client.Login'],
             excludes=[
    'sphinx', 'cython',
    '_gtkagg', '_tkagg', 'bsddb', 'curses', 'pywin.debugger', 'pandas',
    'pywin.debugger.dbgcon', 'pywin.dialogs', 'tcl', 'Tkconstants', 'tkinter'],

    hookspath=None,
    runtime_hooks=None)

# to prevent the error: 'WARNING: file already exists but should not:
# ...pyconfig.h'
for d in a.datas:
    if 'pyconfig' in d[0]:
        a.datas.remove(d)
        break


dfiles = addDataFiles()
a.datas += dfiles

# remove dlls that were added in win10 but not in win7:
# import platform
# if platform.platform().startswith("Windows-10"):

def keep(x):
    for dll in ('mkl_mc', 'mkl_vml', 'mkl_tbb', 'mkl_sequential', 
                    'mkl_avx','mkl_rt'):
        if dll in x[0]:
            return False
    return True


a.binaries = [x for x in a.binaries if keep(x)]

#tifffiles extension module is for some reason  not included automatically
# do that manually now:
import _tifffile
tifffpath = _tifffile.__file__
del _tifffile
a.binaries += [ (os.path.basename(tifffpath), tifffpath, 'BINARY') ]

#TODO: this keeps many pyqtgraph files, that ARE NOT in client\\pyqtgraph
def isDataFile(i):
    for f in dfiles:
        fpath = f[0]
        if fpath.startswith('client\\'):
            
            if (i[1].endswith(fpath) 
                or  ('\\' in fpath[7:] and i[1].endswith(fpath[7:]))):
                return True
    return False

a.pure = [x for x in a.pure if not isDataFile(x)]
# 
# for i in a.pure:
#     print(i)


pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=1,
    name='QELA.exe',
    debug=False,##
    strip=False,
    upx=False,
    console=False,##
    icon=os.path.join(pkg_dir, 'qelaClient', 'QELAclient',
                      'client', 'media', 'logo.ico'))

dist = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               name="QELA")


# write version.txt, so first time client is updated and not fully downloaded:
with open(os.path.join(DISTPATH,  'QELA', 'client', 'version.txt'), 'w') as f:
    f.write(time.strftime("%x %X", time.gmtime()))
