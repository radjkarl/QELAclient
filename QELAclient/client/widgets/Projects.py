# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets, QtCore, QtGui

from client.widgets.ButtonGroupBox import ButtonGroupBox


class PNameValidator(QtGui.QValidator):

    def validate(self, txt, pos):
        txt, pos = QtGui.QValidator.validate(self, txt, pos)
        if 0 < len(txt) < 500 and txt != '[current]':
            # only allow asci txt
            return QtGui.QValidator.Acceptable, pos
        return QtGui.QValidator.Invalid, pos


class Projects(QtWidgets.QWidget):
    '''
    todo: writeexplanatory text here
    '''
    
    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.setWindowTitle('Change current project')
        self.setWindowIcon(gui.windowIcon())
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)

        self.resize(300, 150)

        lay = QtWidgets.QVBoxLayout()
        lay.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(lay)

        lab = QtWidgets.QLabel("Current project: ")
        self._cb = cb = QtWidgets.QComboBox()
        cb.setInsertPolicy(QtWidgets.QComboBox.InsertAtCurrent)

        cb.setEditable(True)
        cb.lineEdit().setValidator(PNameValidator())

        btn = QtWidgets.QPushButton()
        btn.setFlat(True)
        btn.setIcon(
            QtWidgets.QApplication.style().standardIcon(
                QtWidgets.QStyle.SP_FileDialogNewFolder))
        btn.clicked.connect(self._addProject)

        l1 = QtWidgets.QHBoxLayout()
        l1.addWidget(lab)
        l1.addWidget(cb)
        l1.addWidget(btn)
        lay.addLayout(l1)

        self._labInfo = QtWidgets.QLabel()
        box = ButtonGroupBox(topleft=False)
        box.btn.setIcon(QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.SP_TitleBarCloseButton))
        box.btn.clicked.connect(self._removeProject)
        l0 = QtWidgets.QVBoxLayout()
        box.setLayout(l0)
        l0.addWidget(self._labInfo)
        lay.addWidget(box)

        if gui:
            cb.addItems(gui.server.projectList())
            self._cb.setCurrentText(self.gui.server.projectName())
            cb.currentIndexChanged.connect(self._changeProject)
            cb.lineEdit().editingFinished.connect(self._renameProject)
        else:
            # only for debugging:
            cb.addItems(['a', 'b', 'c'])
            self.show = super().show

    def show(self):
        self._updateProjectInfo()
        super().show()

    def _removeProject(self):
        name = self._cb.currentText()
        res = QtWidgets.QMessageBox.question(
            self, 'Remove project "%s"' % name, 'Are you sure?')
        if res == QtWidgets.QMessageBox.Yes:
            self.gui.server.projectRemove()
            self._cb.removeItem(self._cb.currentIndex())
            self._changeProject()

    def _changeProject(self, index=None):
        if index is None:
            name = self._cb.currentText()
        else:
            name = self._cb.itemText(index)
        if not name:
            return
        
        self.gui.server.projectSet(name)
        self._updateProjectInfo()

        self.gui.updateWindowTitle(project=name)
        self.gui.restoreConfigFromServer()
        self.gui.tabCheck.checkUpdates()
        self.gui.updateProjectFolder()
        self.gui.tabDownload.fileTableView.rootPathChanged()

    def _updateProjectInfo(self):
        s = ''
        for key, val in self.gui.server.projectInfo():
            s += '%s: %s\n' % (key, val)
        self._labInfo.setText(s[:-1])

    def _addProject(self):
        name = QtWidgets.QInputDialog.getText(
            self, 'Add new project', 'Project name')[0]
        if name:
            self.gui.server.projectSet(name)
            self._cb.addItem(name)
            self._cb.setCurrentText(name)
            self.gui.updateWindowTitle(project=name)

    def _renameProject(self):
        name = self._cb.currentText()
        self.gui.server.projectRename(name)
        self.gui.updateWindowTitle(project=name)


if __name__ == '__main__':
    from client.Application import Application

    app = Application()
    w = Projects(None)
    w.show()
    app.exec_()