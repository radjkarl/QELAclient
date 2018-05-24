from PyQt5 import QtWidgets, QtCore, QtGui
from client.items import FilenamesValidator


class _LineEditCheck(QtWidgets.QLineEdit):

    def __init__(self):
        super().__init__()
        self.textChanged.connect(self._check)

    def _check(self):
        p = self.palette()
        if self.hasAcceptableInput():
            p.setColor(QtGui.QPalette.Text, QtCore.Qt.black)
        else:
            p.setColor(QtGui.QPalette.Text, QtCore.Qt.red)
        self.setPalette(p)


class LineEditPhoneNumber(_LineEditCheck):

    def __init__(self):
        super().__init__()
        self.setPlaceholderText('+65 123456879')

        r = QtCore.QRegExp(
            "^([0|\+[0-9]{1,5})?([0-9]{10})$")
        r.setPatternSyntax(QtCore.QRegExp.RegExp)
        self.setValidator(QtGui.QRegExpValidator(r))
        self.setToolTip('Every mobile phone number can be only used once.')


class LineEditMail(_LineEditCheck):

    def __init__(self):
        super().__init__()
        self.setPlaceholderText('my@mail.sg')

        r = QtCore.QRegExp(
            "\\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,4}\\b")
        r.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        r.setPatternSyntax(QtCore.QRegExp.RegExp)
        self.setValidator(QtGui.QRegExpValidator(r))


class LineEditPassword(_LineEditCheck):

    def __init__(self):

        super().__init__()
        self.setToolTip(
            "Minimum length: 7, should contain at least 1 number and mixed upper/lowercase")

        self.setEchoMode(QtWidgets.QLineEdit.Password)
        self.setInputMethodHints(QtCore.Qt.ImhHiddenText | 
                                 QtCore.Qt.ImhNoPredictiveText | 
                                 QtCore.Qt.ImhNoAutoUppercase)

    def hasAcceptableInput(self):
        s = self.text()
        return (any(x.isupper() for x in s) and
                any(x.islower() for x in s) and
                any(x.isdigit() for x in s) and len(s) >= 7)


class DialogNewUser(QtWidgets.QDialog):

    def __init__(self, name="", pwd="", mobile="", mail=""):
        super().__init__()
        self.setWindowTitle('Register new user')

        lg = QtWidgets.QGridLayout()
        self.setLayout(lg)

        l0 = QtWidgets.QLabel('User name:')
        self.eUser = e0 = QtWidgets.QLineEdit()
        e0.setText(name)
        e0.setToolTip(
            'The user name will be used to identify the user. It must not exist already.')

        l1 = QtWidgets.QLabel('Password:')
        self.ePwd = e1 = LineEditPassword()
        e1.setText(pwd)

        l2 = QtWidgets.QLabel('Mobile phone number:')
        self.editNumber = e2 = LineEditPhoneNumber()
        e2.setText(mobile)

        l3 = QtWidgets.QLabel('Email:')
        self.editMail = e3 = LineEditMail()
        e3.setText(mail)

        self.btnLogin = b0 = QtWidgets.QPushButton("Submit")
        b1 = QtWidgets.QPushButton("Cancel")

        lg.addWidget(l0, 0, 0)
        lg.addWidget(l1, 1, 0)

        lg.addWidget(e0, 0, 1)
        lg.addWidget(e1, 1, 1)

        lg.addWidget(l2, 2, 0)
        lg.addWidget(l3, 3, 0)

        lg.addWidget(e2, 2, 1)
        lg.addWidget(e3, 3, 1)

        lg.addWidget(b0, 4, 0)
        lg.addWidget(b1, 4, 1)

        b0.setEnabled(False)

        b0.clicked.connect(self.OK)
        b1.clicked.connect(self.cancel)

        e0.textChanged.connect(self._checkInput)
        e1.textChanged.connect(self._checkInput)
        e2.textChanged.connect(self._checkInput)
        e3.textChanged.connect(self._checkInput)

        self.fields = self.eUser, self.ePwd, self.editNumber, self.editMail

    def _checkInput(self):
        self.btnLogin.setEnabled(all([i.hasAcceptableInput()
                                      for i in self.fields]))

    def OK(self):
        self.result = [i.text() for i in self.fields]
        self.close()

    def cancel(self):
        self.result = None
        self.close()


class FilenameInputDialog(QtWidgets.QDialog):

    def __init__(self, title, text):
        super().__init__()
        self.setWindowTitle(title)
        lg = QtWidgets.QVBoxLayout()
        self.setLayout(lg)
        l0 = QtWidgets.QLabel(text)

        self._ed = ed = QtWidgets.QLineEdit()
        ed.setValidator(FilenamesValidator(self))
        bb = QtWidgets.QDialogButtonBox
        btns = bb(bb.Ok | bb.Cancel)
        lg.addWidget(l0)
        lg.addWidget(ed)
        lg.addWidget(btns)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        self._btnOK = btns.button(bb.Ok)
        self._btnOK.setEnabled(False)
        ed.textChanged.connect(self._checkEenableOK)

    def _checkEenableOK(self):
        self._btnOK.setEnabled(len(self._ed.text()) > 0)

    def text(self):
        return self._ed.text()


class DialogExistingUser(QtWidgets.QDialog):

    def __init__(self, user=None):
        super().__init__()
        self.setWindowTitle('Login existing user')
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

        self.btnLogin = b0 = QtWidgets.QPushButton("Login")
        b1 = QtWidgets.QPushButton("Cancel")

        lg.addWidget(l0, 0, 0)
        lg.addWidget(l1, 1, 0)
        lg.addWidget(e0, 0, 1)
        lg.addWidget(e1, 1, 1)
        lg.addWidget(b0, 2, 0)
        lg.addWidget(b1, 2, 1)

        if user is not None:
            e0.setText(user)
            e1.setFocus()

        b0.setEnabled(False)

        b0.clicked.connect(self.OK)
        b1.clicked.connect(self.cancel)

        e0.textChanged.connect(self.checkInput)
        e1.textChanged.connect(self.checkInput)

    def checkInput(self):
        self.btnLogin.setEnabled(
            bool(self.eUser.text()) and bool(self.ePwd.text()))

    def OK(self):
        t0, t1 = self.eUser.text(), self.ePwd.text()
        self.result = t0, t1
        self.close()

    def cancel(self):
        self.result = None
        self.close()


class ForgotAccess(QtWidgets.QDialog):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Forgot access data')
        self.email = None
        lg = QtWidgets.QGridLayout()
        self.setLayout(lg)
        
        txt = QtWidgets.QLabel("""No worries, we will send a mail to you 
with username and password""")
        
        l0 = QtWidgets.QLabel('Your email address:')
        
        self.eMail = e0 = LineEditMail()
        
        self.btnConnect = b0 = QtWidgets.QPushButton("Send mail")
        b1 = QtWidgets.QPushButton("Cancel")

        lg.addWidget(txt, 0, 0, 1, 2)
        
        lg.addWidget(l0, 1, 0)
        
        lg.addWidget(e0, 1, 1)
        
        lg.addWidget(b0, 3, 0)
        lg.addWidget(b1, 3, 1)

        b0.clicked.connect(self.OK)
        b1.clicked.connect(self.cancel)

        e0.textChanged.connect(self.checkInput)

    def checkInput(self):
        self.btnConnect.setEnabled(self.eMail.hasAcceptableInput())

    def OK(self):
        self.email = self.eMail.text()
        self.close()

    def cancel(self):
        self.setResult(0)
        self.close()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    w = DialogNewUser()
    w2 = DialogExistingUser()
    w3 = FilenameInputDialog('aaa', 'ccc')

    w.show()
    w2.show()
    w3.show()

    app.exec_()
