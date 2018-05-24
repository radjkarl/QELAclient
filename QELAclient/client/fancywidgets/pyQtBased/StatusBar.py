# coding=utf-8
from PyQt5 import QtGui, QtWidgets, QtCore


class StatusBar(QtWidgets.QStatusBar):

    def __init__(self):
        QtWidgets.QStatusBar.__init__(self)

        # do not resize mainWindow when a longer message is displayed:
        self.setMinimumWidth(2)
        self.setFixedHeight(self.sizeHint().height() + 5)
        l = self.layout()
        l.setSpacing(0)
        l.setContentsMargins(0, 0, 0, 0)

        self._pMsg = QtGui.QPalette()
        self._pMsg.setColor(QtGui.QPalette.Foreground, QtCore.Qt.black)
        self._pErr = QtGui.QPalette()
        self._pErr.setColor(QtGui.QPalette.Foreground, QtCore.Qt.red)

    def showMessage(self, msg, time_ms=9000):
        self.setPalette(self._pMsg)
        return self._show(msg, time_ms)

    def showError(self, msg, time_ms=9000):
        '''
        Show error message in red color
        '''
        self.setPalette(self._pErr)
        return self._show(msg, time_ms)

    def _show(self, msg, time_ms):
        try:
            msg = msg.decode()
        except AttributeError:
            pass
        if msg != '\n':
            if '\n' in msg:
                # show only last line:
                msg = msg.split('\n')[-2]
            return QtWidgets.QStatusBar.showMessage(self, msg, time_ms)
