# coding=utf-8
# foreign
from PyQt5 import QtWidgets, QtCore
# this pkg
from fancywidgets.pyQtBased._textEditorUtils import ToolBarFormat, ToolBarInsert, MainWindow  # ToolBarFont


class FwMinimalTextEditor(MainWindow):

    def __init__(self, parent=None):
        MainWindow.__init__(self, parent)

        self.text.setTabStopWidth(12)
        self.setCentralWidget(self.text)
#         self.addToolBar(ToolBarFont(self.text))

#         self.addToolBarBreak()
        toolBar = ToolBarFormat(self.text)
        self.addToolBar(toolBar)

        toolBarInsert = ToolBarInsert(self.text)
        self.addToolBar(toolBarInsert)

        toolBarInsert.setIconSize(QtCore.QSize(16, 16))
        toolBar.setIconSize(QtCore.QSize(16, 16))


if __name__ == "__main__":
    import sys
    #######################
    # temporary fix: app crack doesnt through exception
    # https://stackoverflow.com/questions/38020020/pyqt5-app-exits-on-error-where-pyqt4-app-would-not
    sys.excepthook = lambda t, v, b: sys.__excepthook__(t, v, b)
    #######################
    app = QtWidgets.QApplication(sys.argv)
    w = FwMinimalTextEditor()
    w.setWindowTitle(w.__class__.__name__)

    w.show()
    app.exec_()
