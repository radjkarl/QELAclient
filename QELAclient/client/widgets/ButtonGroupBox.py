from PyQt5 import QtWidgets


class ButtonGroupBox(QtWidgets.QGroupBox):

    def __init__(self, *args, topleft=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.btn = QtWidgets.QPushButton(self)
        self.btn.resize(13, 13)
        if topleft:
            self.btn.move(-2, -2)
        else:
            self.resizeEvent = self._resizeEvent_topRight

    def _resizeEvent_topRight(self, _evt):
        self.btn.move(self.width() - self.btn.width(), -2)
