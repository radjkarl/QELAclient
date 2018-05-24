import sys
import json
import time
import base64
from PyQt5 import QtWidgets, QtGui, QtCore

from fancytools.utils.Logger import Logger

# LOCAL:
from client import ICON, PATH
from client.widgets.About import About
from client.widgets.MainWindow import MainWindow
from client.dialogs import LineEditPassword, LineEditPhoneNumber, LineEditMail, ForgotAccess

#######################
# temporary fix: app crack doesnt through exception
# https://stackoverflow.com/questions/38020020/pyqt5-app-exits-on-error-where-pyqt4-app-would-not
sys.excepthook = lambda t, v, b: sys.__excepthook__(t, v, b)
#######################

MAXLOGS = 7
flogs = PATH.mkdir('logs')
fils = list(flogs.files())
try:
    if len(fils) > MAXLOGS:
        # remove some old logs
        for f in fils[-MAXLOGS::-1]:
            f.remove()
except PermissionError:
    # could not remove old log, because another client is open
    pass
else:
    sys.stderr = Logger(sys.stderr,
                        flogs.join(time.strftime("%Y_%m_d__%H_%M_%S",
                                                 time.localtime()) + '.txt'))


class Login(QtWidgets.QTabWidget):

    def __init__(self, server, noautologin=False):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.Window
                            | QtCore.Qt.WindowCloseButtonHint)
        self.server = server
        self.user = self.server.user()
        self.pwd = None
        self._started = False
        if self.user != "None":
            # no need to log in, if user is still logged in:
            QtCore.QTimer.singleShot(0, self._start)
#             self.hide()
        else:
            config = _Config()
            self.setWindowIcon(QtGui.QIcon(ICON))
            self.setWindowTitle('Starting QELA')
            # login and register tab:
            self.tabLogin = _TabLogin(self.server, config, noautologin)
            self.tabLogin.sigSuccess.connect(self._start)
            self.tabRegister = _TabRegister(self.server, self)
            self.addTab(self.tabLogin, "Login")
            self.addTab(self.tabRegister, "Register")
            # about button/win:
            self._about = None
            btnAbout = QtWidgets.QPushButton(self)
            btnAbout.setFlat(True)
            btnAbout.clicked.connect(self._showAbout)
            btnAbout.setIcon(QtWidgets.QApplication.style().standardIcon(
                QtWidgets.QStyle.SP_MessageBoxInformation))
            self.setCornerWidget(btnAbout)
        # delay show, to auto-login can run first
        QtCore.QTimer.singleShot(10, self._checkShow)

    def _checkShow(self):
        if not self._started:
            self.show()

    def _showAbout(self):
        if self._about is None:
            self._about = About(self)
        self._about.show()
        self._about.move(self.frameGeometry().bottomLeft())

#     def show(self, *args, **kwargs):
#         # show login on center of primary screen
#         # this supposedly overcomes  to scaling probled caused by mixed high DPI 
#         # and normal screens
#         app = QtWidgets.QApplication.instance()
#         w, h = self.size().width() // 2, self.size().height() // 2
#         c = app.desktop().screenGeometry(1).center() 
#         c.setX(c.x() - w)
#         c.setY(c.y() - h)
# 
#         self.move(c)
#         
#         super().show(*args, **kwargs)

    def _start(self):
        self._started = True
        self.close()
        user = self.user
        pwd = None
        if user == 'None':
            user = self.tabLogin.eUser.text()
            pwd = self.tabLogin.ePwd.text()

        _ = MainWindow(self, self.server, user, pwd)


class _TabLogin(QtWidgets.QWidget):
    sigSuccess = QtCore.pyqtSignal()

    def __init__(self, server, config, noautologin):
        super().__init__()

        self.server = server
        self.config = config
        lg = QtWidgets.QGridLayout()
        self.setLayout(lg)
        l0 = QtWidgets.QLabel('User name:')

        l1 = QtWidgets.QLabel('Password:')
        self.eUser = e0 = QtWidgets.QLineEdit()

        self.ePwd = e1 = QtWidgets.QLineEdit()
        e1.setEchoMode(QtWidgets.QLineEdit.Password)
        e1.setInputMethodHints(QtCore.Qt.ImhHiddenText | 
                               QtCore.Qt.ImhNoPredictiveText | 
                               QtCore.Qt.ImhNoAutoUppercase)

        users = config['users']
        luser = config['last user']
        if users:
            completer = QtWidgets.QCompleter(users)
            e0.setCompleter(completer)
            if luser is None:
                luser = users[0]
            e0.setText(luser)
            e1.setFocus()

        self.btn = b0 = QtWidgets.QPushButton("Login")
        self.btn.clicked.connect(self.login)
        
        btn_forgot = QtWidgets.QPushButton('Forgot login details?')
        btn_forgot.clicked.connect(self._forgotClicked)
        btn_forgot.setFlat(True)
        btn_forgot.setStyleSheet("""QPushButton {
    text-decoration: underline;
    text-align:right;}""")

        if luser and not noautologin:
            # try to auto login in case password file exists:
            fpwd = PATH.join(luser, 'pwd')
            if fpwd.exists():
                with open(fpwd, 'rb') as f:
                    self.ePwd.setText(base64.b64decode(f.read()).decode())
                QtCore.QTimer.singleShot(0, self.login)
        self.btn.setEnabled(False)

        lg.addWidget(l0, 0, 0)
        lg.addWidget(l1, 1, 0)
        lg.addWidget(e0, 0, 1)
        lg.addWidget(e1, 1, 1)
        lg.addWidget(b0, 2, 0)
        lg.addWidget(btn_forgot, 2, 1, alignment=QtCore.Qt.AlignRight)

        e0.textChanged.connect(self.checkInput)
        e1.textChanged.connect(self.checkInput)

        self.fields = (e0, e1)

        QtCore.QTimer.singleShot(100, self._setFocus)

    def _forgotClicked(self):
        f = ForgotAccess()
        f.exec_()
        if f.email is not None:
            answer = self.server.forgotAccess(f.email)

            MBox = QtWidgets.QMessageBox
            if answer != 'OK':
                msg = MBox(MBox.Critical, 'ERROR', answer)
            else:
                msg = MBox(MBox.Information, 'Alright',
                           """An email has been send to your account. Please check.""")
            msg.exec_()

    def _setFocus(self):
        if self.eUser.text():
            self.ePwd.setFocus()

    def keyPressEvent(self, evt):
        if evt.key() == QtCore.Qt.Key_Return and self.btn.isEnabled():
            self.login()

    def checkInput(self):
        self.btn.setEnabled(
            bool(self.eUser.text()) and
            bool(self.ePwd.text()))

    def login(self):
        user = self.eUser.text()
        answer = self.server.login(user, self.ePwd.text())
        if answer == 'OK':
            self.btn.setText('Please wait...')

            self.config.writeUser(user)
            if self.twoFacAutorization():
                self.sigSuccess.emit()
        else:
            msg = QtWidgets.QMessageBox()
            msg.setText(answer)
            msg.exec_()

    def twoFacAutorization(self):
        MAX_ATTEMPTS = 5
        answer = self.server.requires2FA()
        if not answer:
            return True
        code, res = QtWidgets.QInputDialog.getText(
            self, 'Log in via 2 factor authorization (2FA)',
            '''A message has been send your mobile device.
Please enter code found in that message. 
You can switch off 2FA at Menu->Security''', text='verification code',
            inputMethodHints=QtCore.Qt.ImhPreferNumbers)
        for _ in range(MAX_ATTEMPTS):
            if not res:
                print("Log in canceled")
                return False
            if not self.server.verifyOTP(code) == 'OK':
                code, res = QtWidgets.QInputDialog.getText(
                    self, 'Log in via 2 factor authorization',
                    '''The entered code is not correct.
Another message has been send your mobile device.
Please enter code found in that message.''', text='verification code',
                    inputMethodHints=QtCore.Qt.ImhPreferNumbers)
            else:
                return True


class _TabRegister(QtWidgets.QWidget):

    def __init__(self, server, tabs):
        super().__init__()

        self.server = server
        self.tabs = tabs

        lg = QtWidgets.QGridLayout()
        self.setLayout(lg)

        l0 = QtWidgets.QLabel('User name:')
        self.eUser = e0 = QtWidgets.QLineEdit()
        e0.setToolTip(
            'The user name will be used to identify the user. It must not exist already.')

        l1 = QtWidgets.QLabel('Password:')
        self.ePwd = e1 = LineEditPassword()

        l2 = QtWidgets.QLabel('Mobile phone number:')
        self.editNumber = e2 = LineEditPhoneNumber()

        l3 = QtWidgets.QLabel('Email:')
        self.editMail = e3 = LineEditMail()

        self.btn = QtWidgets.QPushButton("Register")

        self.btn.setEnabled(False)

        lg.addWidget(l0, 0, 0)
        lg.addWidget(l1, 1, 0)

        lg.addWidget(e0, 0, 1)
        lg.addWidget(e1, 1, 1)

        lg.addWidget(l2, 2, 0)
        lg.addWidget(l3, 3, 0)

        lg.addWidget(e2, 2, 1)
        lg.addWidget(e3, 3, 1)

        lg.addWidget(self.btn, 4, 0)

        self.btn.clicked.connect(self.register)

        e0.textChanged.connect(self.checkInput)
        e1.textChanged.connect(self.checkInput)
        e2.textChanged.connect(self.checkInput)
        e3.textChanged.connect(self.checkInput)

        self.fields = self.eUser, self.ePwd, self.editNumber, self.editMail

    def keyPressEvent(self, evt):
        if evt.key() == QtCore.Qt.Key_Return and self.btn.isEnabled():
            self.register()

    def checkInput(self):
        self.btn.setEnabled(all([i.hasAcceptableInput()
                                 for i in self.fields]))

    def register(self):
        result = [i.text() for i in self.fields]
        answer = self.server.register(*result)
        MBox = QtWidgets.QMessageBox
        if answer != 'OK':
            msg = MBox(MBox.Critical, 'ERROR during registration',
                       answer)
            msg.exec_()
        else:
            msg = MBox(MBox.Information, 'Almost ready ...',
                       """Thanks for registering.
You will shortly receive a mail to verify your address.
Please click on the link provided.""")

            msg.exec_()
            self.tabs.tabLogin.eUser.setText(result[0])
            self.tabs.setCurrentWidget(self.tabs.tabLogin)


class _Config(dict):

    # dict, which also writes to file "config.txt"
    def __init__(self):
        super().__init__()
        self.path = PATH.join("config.txt")

        try:
            with open(self.path, 'r') as f:
                try:
                    self.update(json.loads(f.read()))
                except Exception:
                    print('config file broken')
                    raise FileNotFoundError()
        except FileNotFoundError:
            self.update({'users': [], 'last user': None})

    def _writeConfig(self):
        with open(self.path, 'w') as f:
            f.write(json.dumps(self))

    def writeUser(self, user):
        if user not in self['users']:
            self['users'].append(user)
        self['last user'] = user
        self._writeConfig()


if __name__ == '__main__':
    import socket
    from dAwebAPI.WebAPI import WebAPI
    from client.Application import Application
    
    app = Application()

    HOST, PORT = socket.gethostbyname(socket.gethostname()), 443  # local
    
    HOST, PORT = '172.21.48.124', 80  # 'localhost'  # 
    HOST, PORT = '192.168.56.1', 443  # 'localhost'  # 

    HOST = '203.126.238.251'
    PORT = 443
    conn = WebAPI(HOST, PORT)

    L = Login(conn)

    app.exec_()
