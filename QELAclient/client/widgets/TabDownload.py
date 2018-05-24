import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui

from fancytools.os.PathStr import PathStr

# Local:
from client.widgets.FileTableView import FileTableView
from client import IO_


class TabDownload(QtWidgets.QWidget):
    '''
    To download corrected EL images, statistical data and PDF reports of all processed
    measurements of the current project double-click on your row of choice.
    
    To download/sync all files on your local PC, click  on <Sync all files> on the top right.
    
    To only display EL images of PDF reports,  select a <filter> on the top left.
    '''

    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        ll = QtWidgets.QHBoxLayout()
        self.setLayout(ll)
        self._dFiles = []

        self._timerFiles = QtCore.QTimer()
        self._timerFiles.setInterval(1000)
        self._timerFiles.timeout.connect(self._checkFiles)
        self._timerFiles.start()
        self.labelLocalPath = QtWidgets.QLabel('Local file path: ')

        leftL = QtWidgets.QVBoxLayout()
        lSyn = QtWidgets.QHBoxLayout()

        self.fileTableView = _MyFileTableView(
            gui, self._fnDownload, self.gui.verifyFile)

        self.btnSync = QtWidgets.QPushButton('Sync All Files')
        self.btnSync.clicked.connect(lambda: self.fileTableView.sync())

        self.btnSync.setEnabled(False)

        btnPathChange = QtWidgets.QPushButton('Change')
        btnPathChange.setToolTip('Change the local download  directory.')
        btnPathChange.clicked.connect(self._chooseRootPath)

        self.cbFilter = QtWidgets.QComboBox()
        self.cbFilter.addItems(['-', 'Reports', 'EL images', 'Scaled EL images'])
        self.cbFilter.currentTextChanged.connect(self.fileTableView.setFilter)

        lSyn.addWidget(QtWidgets.QLabel('Filter:'))
        lSyn.addWidget(self.cbFilter)
        lSyn.addStretch()
        lSyn.addWidget(self.labelLocalPath)
        lSyn.addWidget(btnPathChange)
        lSyn.addStretch()

        self.labelFiles = lab = QtWidgets.QLabel()

        lSyn.addWidget(lab)
        lSyn.addWidget(self.btnSync)
        leftL.addLayout(lSyn, stretch=0)
        leftL.addWidget(self.fileTableView, stretch=1)
        ll.addLayout(leftL, stretch=1)

    def _checkFiles(self):
        if not self.isVisible() or not self.gui.server.isReady():
            return
        if self.gui.server.hasNewFiles():
            self.fileTableView.updateServerFiles(self.gui.server.availFiles())
            self.updateStats()

    def updateStats(self):
        (nlocal, nserver, noutdated,
         slocal, sserver, soutdated) = self.fileTableView.stats()

        col0 = self.fileTableView.COL_NOTEXISTANT
        col1 = self.fileTableView.COL_OUTDATED
        self.labelFiles.setText("{} Local ({}) \
<font color='{}'> {} Server ({})  </font> \
<font color='{}'> {} Outdated ({}) </font>".format(nlocal, slocal,
                                                   QtGui.QColor(col0).name(),
                                                   nserver, sserver,
                                                   QtGui.QColor(col1).name(),
                                                   noutdated, soutdated))

        self.btnSync.setEnabled(nserver or noutdated)

    def _fnDownload(self, paths, root, fnDone):
        self._timerFiles.stop()
        self.gui.addDownload(paths, root, (fnDone, self._downloadDone))

    def _downloadDone(self):
        self._timerFiles.start()
        self.updateStats()

    def _chooseRootPath(self):
        r = self.gui.root
        new_r = QtWidgets.QFileDialog.getExistingDirectory(directory=r)
        if new_r:
            self._changeRootPath(new_r)

    def _changeRootPath(self, new_r):
        self.gui.root = PathStr(new_r)
        self.fileTableView.rootPathChanged(False)  
        self._updateFilePathLabel()

    def _updateFilePathLabel(self):
        self.labelLocalPath.setText('Local file path: %s' % self.gui.root)

    def activate(self):
        self.fileTableView.show()
        self._checkFiles()
        self._updateFilePathLabel()

    def saveState(self):
        return {'root':self.gui.root,
                'filter':self.cbFilter.currentText()}

    def restoreState(self, state):
        self._changeRootPath(state['root'])
        # TODO: doesnt apply filter on startup:
#         self.cbFilter.setCurrentText(state['filter'])


class _MyFileTableView(FileTableView):

    def __init__(self, gui, *args):
        self.gui = gui
        self._filter = None
        super(). __init__(IO_.hirarchy, self._open, *args)

    def _openNextRow(self):
        r = self.currentRow()
        if r < self.rowCount() - 1:
            self.selectRow(r + 1)
#             path = self.item(r + 1, 0).text()
#             self._open(path)
            self._openSelected()

    def _open(self, path):
        self.gui.openImage(path, prevFn=self._openPrevRow,
                               nextFn=self._openNextRow)

    def _openPrevRow(self):
        r = self.currentRow()
        if r > 0:
            self.selectRow(r - 1)
#             path = self.item(r - 1, 0).text()
            self._openSelected()

    def pathJoin(self, pathlist):
        return IO_.pathJoin(pathlist)

    def pathSplit(self, path):
        return IO_.pathSplit(path)

    def show(self):
        # only exec once:
        self.setLocalPath(self.gui.projectFolder())
        # reset:
        self.show = super().show
        self.show()

    def rootPathChanged(self, projectChanged=True):
        self.setLocalPath(self.gui.projectFolder())
        if projectChanged:
            f = self.gui.server.availFiles()
        else:
            f = None
        self.updateServerFiles(f)

    def setFilter(self, filt):
        # which columns to  show(1)/hide(0)
        if filt == 'Reports':
            h = [0, 1, 1, 1, 0, 1]
            self._filter = 'report'
        elif filt == '-':
            h = [0, 0, 0, 0, 0, 0]
            self._filter = None
        elif filt == 'EL images':
            h = [0, 0, 0, 0, 0, 1]
            self._filter = 'EL.'
        elif filt == 'Scaled EL images':
            h = [0, 0, 0, 0, 0, 1]
            self._filter = 'EL_scaled'
        else:
            raise Exception('Filter type unknown')

        for c, hide in enumerate(h):
            self.setColumnHidden(self.col(c), bool(hide))
        self.update()

    def filter(self, data):
        if self._filter is None:
            return data
        ind = np.char.startswith(data[:, self.col(5)], self._filter)
        return data[ind]
