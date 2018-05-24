from PyQt5 import QtWidgets

from fancywidgets.pyQtBased.FwMinimalTextEditor import FwMinimalTextEditor

# LOCAL
from client import PATH


class Contact(QtWidgets.QWidget):

    def __init__(self, gui=None):
        super().__init__()
        self.setWindowTitle('Write mail to admin')
        self.resize(400, 250)
        if gui:
            self.setWindowIcon(gui.windowIcon())
        self.gui = gui

        l0 = QtWidgets.QVBoxLayout()
        self.setLayout(l0)

        self.btnSubmit = QtWidgets.QPushButton("Submit")
        self.btnSubmit.setEnabled(False)
        self.btnSubmit.clicked.connect(self._submit)

        self.editor = FwMinimalTextEditor()
        self.editor.text.setPlaceholderText('''Your message.
Please include information on ...
* Module ID
* Measurement number and current

The nature of the problem e.g.: 
* features are always detected wrong
* image correction looks odd
* no image visible
* error occurs 

You can add a screenshot of your problem using the <Snipping tool> (top right)''')
        self.editor.text.textChanged.connect(self._checkSubmit)
        self.editor
        l1 = QtWidgets.QHBoxLayout()
        self.subject = QtWidgets.QLineEdit()
        self.subject.setPlaceholderText("Subject")
        self.subject.textChanged.connect(self._checkSubmit)

        l1.addWidget(self.subject)
        l1.addSpacing(1)
        l1.addWidget(self.btnSubmit)

        l0.addLayout(l1)
        l0.addWidget((self.editor))

        self._chLog = QtWidgets.QCheckBox('Include log files')
        self.logsfolder = PATH.join('logs')
        self._chLog.setToolTip('''Check, to also submit error log files. 
This can be helpful, in case your issue refers to a software bug.
You can find the logs file at %s''' % self.logsfolder)
        l0.addWidget(self._chLog)

    def _checkSubmit(self):
        self.btnSubmit.setEnabled(len(self.editor.text.toPlainText())
                                  and len(self.subject.text()))

    def _submit(self):
        logs = ''
        if self._chLog.isChecked():
            logs = '\n\nLOGS:\n'
            for f in self.logsfolder.files():
                with open(f) as f:
                    logs += f.read()
                    logs += '\n'

        msg = '%s\n%s%s\n<EOF>' % (
            self.subject.text(), self.editor.toHtml(), logs)

        self.gui.server.messageToAdmin(msg)

        box = QtWidgets.QMessageBox()
        box.setWindowTitle('Message send')
        box.setText("Your message has been send to the ADMIN.")
        box.exec_()

        self.close()


if __name__ == '__main__':
    import sys
    from PyQt5 import QtCore
    #######################
    # temporary fix: app crack doesnt through exception
    # https://stackoverflow.com/questions/38020020/pyqt5-app-exits-on-error-where-pyqt4-app-would-not
    sys.excepthook = lambda t, v, b: sys.__excepthook__(t, v, b)
    #######################

    QA = QtWidgets.QApplication
    # enable HD DPI monitor support:
    QA.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QA.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication([])
    w = Contact()
    w.show()
    app.exec_()
