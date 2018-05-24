from PyQt5 import QtWidgets


class CancelProgressBar(QtWidgets.QWidget):

    def __init__(self):
        super().__init__()
        self.bar = QtWidgets.QProgressBar()
        self.btn = QtWidgets.QPushButton("Cancel")
        ll = QtWidgets.QHBoxLayout()
        ll.setContentsMargins(0, 0, 0, 0)
        self.setLayout(ll)
        ll.addWidget(self.bar)
        ll.addWidget(self.btn, stretch=0)
#         self._cancel_active = False
#         self.color = 'black'
        self.connectedFn = None

    def setCancel(self, fn=None):
        '''
        enable cancel button
        fn ... function to execute at cancel
        '''
        try:
            self.btn.clicked.disconnect()
        except TypeError:
            pass
#         if fn:
        self.btn.clicked.connect(self.hide)
        self.btn.clicked.connect(fn)

        self.connectedFn = fn
#         self._cancel_active = True

    def setColor(self, name):
        self.bar.setStyleSheet("QProgressBar {color: %s}" % name)
#         self.color = name

    def show(self):
        if self.connectedFn:
            self.btn.show()
        else:
            self.btn.hide()
        super().show()

    def hide(self):
        super().hide()
        self.btn.hide()
        self.bar.setValue(0)
        self.bar.setFormat('')
        self.bar.setStyleSheet('')

#         self.color = 'black'

        if self.connectedFn:
            self.btn.clicked.connect(self.connectedFn)
            self.connectedFn = None
