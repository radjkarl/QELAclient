from PyQt5 import QtWidgets, QtGui


class QMenu(QtWidgets.QMenu):

    # show qaction tooltips by default
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setToolTipsVisible(True)


class QMessageBox(QtWidgets.QMessageBox):

    # adjust size to  given text:
    def setText(self, text):
        QtWidgets.QMessageBox.setText(self, text)
        # get width on longest line:
        width = max(QtGui.QFontMetrics(QtGui.QFont()).boundingRect(line).width() for line in text.split('\n'))
        # enforce that width with a spacer:
        horizontalSpacer = QtWidgets.QSpacerItem(int(width * 1.5), 0, QtWidgets.QSizePolicy.Minimum,
                                             QtWidgets.QSizePolicy.Expanding);
        layout = self.layout()
        layout.addItem(horizontalSpacer, layout.rowCount(),
                       0, 1, layout.columnCount())

    @staticmethod
    def build(parent, buttons=None, title=None, icon=None, text=None):
        box = QMessageBox(parent)
        if buttons is not None:
            box.setStandardButtons(buttons)
        if title is not None:
            box.setWindowTitle(title)
        if text is not None:
            box.setText(text)
        if icon is not None:
            box.setIcon(icon)  
        return box          


if __name__ == '__main__':

    app = QtWidgets.QApplication([])

    L = QMessageBox()
    L.setText('''Changes:
<p0>            <p1>            <old>           <new>
location        <- removed
                    eloss       <- removed
setup           comments                        False          
modules         <- removed''')
    L.exec_()
    app.exec_()
