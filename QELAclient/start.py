import socket
import sys
import json

#######################
# temporary fix: app crack doesnt through exception
# https://stackoverflow.com/questions/38020020/pyqt5-app-exits-on-error-where-pyqt4-app-would-not
sys.excepthook = lambda t, v, b: sys.__excepthook__(t, v, b)
#######################

import importlib
import os
import traceback

from zipfile import ZipFile
from io import BytesIO

from PyQt5 import QtWidgets, QtGui, QtCore


def getcwd():
    try:
        return sys._MEIPASS
    except AttributeError:
        return os.getcwd()


cl_path = os.path.join(getcwd(), 'client')
if not os.path.exists(cl_path):
    os.mkdir(cl_path)
serv_path = os.path.join(cl_path, 'server_address.txt')

sys.path.insert(0, cl_path)

# TODO:
# try:
#     # use dynamically updated sert.py rather than this one, which can be out of date
#     import client.start
# except Exception:
#     pass

from dAwebAPI.WebAPI import WebAPI 

# TODO: replace with final IP
HOST, PORT = '203.126.238.251', 443
if os.path.exists(serv_path):
    try:
        with open(serv_path, 'r')as f:
            d = json.loads(f.read())
            HOST = d['HOST']
            PORT = d['PORT']
    except Exception as e:
        print(e)
# HOST = '192.168.56.1'
HOST, PORT = '203.126.238.251', 443


class _HostAdressDialog(QtWidgets.QDialog):

    def __init__(self, errtxt):
        super().__init__()
        self.setWindowTitle('ERROR')
        self.out = None
        
        lg = QtWidgets.QGridLayout()
        self.setLayout(lg)
        
        txt = QtWidgets.QLabel("""Failed connecting to server.
        
Error message: 
--------------------------------------------------------------
%s
--------------------------------------------------------------

Please ensure you are connected to the Internet.
If you received info on  a new server address, please change now:
""" % errtxt)
        
        l0 = QtWidgets.QLabel('Address:')
        l1 = QtWidgets.QLabel('Port:')
        
        self.eHost = e0 = QtWidgets.QLineEdit()
        self.ePort = e1 = QtWidgets.QLineEdit()
        
        e1.setValidator(QtGui.QIntValidator())
        e0.setText(HOST)
        e1.setText(str(PORT))
        
        self.btnConnect = b0 = QtWidgets.QPushButton("Connect")
        b1 = QtWidgets.QPushButton("Cancel")

        lg.addWidget(txt, 0, 0, 1, 2)
        
        lg.addWidget(l0, 1, 0)
        lg.addWidget(l1, 2, 0)
        
        lg.addWidget(e0, 1, 1)
        lg.addWidget(e1, 2, 1)
        
        lg.addWidget(b0, 3, 0)
        lg.addWidget(b1, 3, 1)

#         b0.setEnabled(False)

        b0.clicked.connect(self.OK)
        b1.clicked.connect(self.cancel)

        e0.textChanged.connect(self.checkInput)
        e1.textChanged.connect(self.checkInput)

    def checkInput(self):
        self.btnConnect.setEnabled(
            bool(self.eHost.text()) and bool(self.ePort.text()))

    def OK(self):
        t0, t1 = self.eHost.text(), int(self.ePort.text())
        self.out = t0, t1
#         self.setResult(1)
        
        self.close()

    def cancel(self):
        self.setResult(0)
#         self.out = None
        self.close()


class _StartThread(QtCore.QThread):
    sigUpdate = QtCore.pyqtSignal(str)
    sigError = QtCore.pyqtSignal(str)
    sigDone = QtCore.pyqtSignal(object, object)  # start module, connection

    def run(self):

        self.sigUpdate.emit('Connect to server')

        try:
            conn = WebAPI(HOST, PORT)
        except Exception as e:
            return self.sigError.emit(str(e))
              
        def version():
            try:
                with open(os.path.join(cl_path, 'version.txt'), 'r') as f:
                    return f.read()
            except Exception:
                return ''

        def update(ver):
            self.sigUpdate.emit('Checking for updates')
            try:

                buffer = conn.getClient(ver)
                if buffer != b'0':
                    self.sigUpdate.emit('Unzip client')

                    with ZipFile(BytesIO(buffer)) as myzip:
                        myzip.extractall(cl_path)

                self.sigUpdate.emit('Starting...')

                client = importlib.import_module('client')
                client.__version__ = ver

                mod = importlib.import_module('Login')

                self.sigDone.emit(mod, conn)
                
            except Exception as e:
                traceback.print_exc()
                return e

        err = update(version())
        if err:
            # could not start program with updating existing client folder
            # no try do receive full client in hope it will work now:
            err = update('')  # try to get client without date given
            if err:
                self.sigError.emit(str(err))


if __name__ == '__main__':
    
    ICON = os.path.join(getcwd(), 'client')
    ICON = os.path.join(ICON, 'media')
    ICON = os.path.join(ICON, 'logo.svg')

    QA = QtWidgets.QApplication
    # enable HD DPI monitor support:
    QA.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QA.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QA([])

    pixmap = QtGui.QPixmap(ICON)
    splash = QtWidgets.QSplashScreen(pixmap)
    splash.show()

    def fnDone(mod, conn):
        fnDone._l = mod.Login(conn)
        splash.close()
        
    def fnError(errtxt):
        # in case  of error:
        # ask for new address
        # Connect -> try to  login again
        # Cancel -> Stop
        splash.showMessage('ERROR')
        d = _HostAdressDialog(errtxt)
        res = d.exec_()

        if d.out is None:
            app.quit()
        else:
            HOST, PORT = d.out
            
            with open(serv_path, 'w')as f:
                f.write(json.dumps({'HOST':HOST, 'PORT':PORT }))
            # restart:
            python = sys.executable
            os.execl(python, python, *sys.argv)
            os._exit(1)

    th = _StartThread()
    th.sigDone.connect(fnDone)
    th.sigUpdate.connect(splash.showMessage)
    th.sigError.connect(fnError)

    th.start()

    sys.exit(app.exec_())

