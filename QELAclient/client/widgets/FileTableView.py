import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui

from fancytools.os.PathStr import PathStr
from fancytools.os import fileSize as fs
from fancytools.utils.dateStr import dateStr
from client.widgets._Base import QMenu


class SortTable(QtWidgets.QTableWidget):
    #     filled = QtCore.pyqtSignal(bool)  # success
    STRING_LEN = 30

    def __init__(self, labels):
        super().__init__(1, len(labels))

        self._cols = list(range(len(labels)))

        # set header:
        for i, l in enumerate(labels):
            item = QtWidgets.QTableWidgetItem(l)
            item.setIcon(QtWidgets.QApplication.style().standardIcon(
                QtWidgets.QStyle.SP_TitleBarUnshadeButton))
            item.sortOrder = 1
            self.setHorizontalHeaderItem(i, item)

        h = self.horizontalHeader()
        h.setSectionResizeMode(h.ResizeToContents)
        h.setStretchLastSection(True)
        h.setSectionsMovable(True)

        h.sectionMoved.connect(self._saveColPoscols)
        h.sectionMoved.connect(self._sort)
        h.sectionClicked.connect(self._changeColSortOrder)

        self.setEditTriggers(self.NoEditTriggers)

    def setData(self, data):
        data = self.filter(data)
        self.setRowCount(len(data))
        for y, row in enumerate(data):
            for x, t in enumerate(row):
                item = QtWidgets.QTableWidgetItem()
                item.setText(t)
                self.setItem(y, x, item)

    def _changeColSortOrder(self, col):
        item = self.horizontalHeaderItem(col)
        st = QtWidgets.QApplication.style()
        if item.sortOrder == 1:
            item.sortOrder = -1
            item.setIcon(st.standardIcon(
                QtWidgets.QStyle.SP_TitleBarShadeButton))
        else:
            item.sortOrder = 1
            item.setIcon(st.standardIcon(
                QtWidgets.QStyle.SP_TitleBarUnshadeButton))

        self._sort()

    def data(self):
        rows, cols = self.rowCount(), self.columnCount()
        out = np.empty(shape=(rows, cols),
                       dtype="<U%i" % self.STRING_LEN)
        for x in range(cols):
            for y in range(rows):
                out[y, x] = self.item(y, x).text()
        return out

    def filter(self, data):
        # dont filter by default // method should be subclassed
        return data

    def setData2(self, data):
        rows, cols = data.shape
        for x in range(cols):
            for y in range(rows):
                self.item(y, x).setText(data[y, x])

    def _saveColPoscols(self, _, ifrom, ito):
        self._cols[ifrom], self._cols[ito] = self._cols[ito], self._cols[ifrom]
#         print(ifrom, ito, self._cols)

    def update(self):
        data = self.filter(self.data())
        self.setData2(data)
        for r in range(len(data)):
            self.setRowHidden(r, False)
        for r in range(len(data), self.rowCount()):
            self.setRowHidden(r, True)

    def _sort(self):
        c = self.rowCount()
        m = self.selectionModel()
        yselect = [index.row() for index in m.selectedRows()]
        d = self.data()
        ll = len(self._cols) - 1
        ind2 = np.arange(c)
        for i, col in zip(range(ll, -1, -1), self._cols[::-1]):
            o = self.horizontalHeaderItem(col).sortOrder
            ind = d[:, self.col(i)].argsort(kind='quicksort'
                                            if i == ll
                                            else 'mergesort')

            d = d[ind][::o]
            # TODO: only move selected indices and not all of them to save some
            # time
            ind2 = ind2[ind][::o]

        self.setData2(d)
        # select lastly selected rows:
        self.clearSelection()
        ss = self.selectionMode()
        self.setSelectionMode(self.MultiSelection)
        [self.selectRow(ind2[yi]) for yi in yselect]
        self.setSelectionMode(ss)

    def col(self, index):
        return self._cols[index]


class FileTableView(SortTable):
    COL_OUTDATED = QtGui.QColor(229, 83, 0)  # dark orange
    COL_NOTEXISTANT = QtCore.Qt.darkGreen

    def __init__(self, labels, fnOpen, fnDownload, fnVerify=None):
        self._n = len(labels)
        labels.extend(['File', 'Local date', 'Server date', 'Size'])
        super().__init__(labels)
        self.setSelectionBehavior(self.SelectRows)
        
        self.fnOpen = fnOpen
        self.fnDownload = fnDownload
        self.fnVerify = fnVerify        
        
        self._serverfiles = []
        self._menu = m = QMenu()
        m.addAction('Open selected file(s)').triggered.connect(
            self._openSelected)
        m.addAction("Open folder(s)").triggered.connect(self._openFolders)
        m.addAction("Copy selected file(s) into new folder").triggered.connect(
            self._copyToNewFolder)
        self.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignLeft)

    def pathSplit(self, path):
        return PathStr.splitNames(path)

    def pathJoin(self, pathlist):
        return PathStr(pathlist[0]).join(*pathlist[1:])

    def setLocalPath(self, path):
        data = self._pathToData(path)
        self.setData(data)

    def _copyToNewFolder(self):
        f = QtWidgets.QFileDialog.getExistingDirectory()
        if f:
            self._tempF = f
            self._downloadDone_backup = self._downloadDone
            self._downloadDone = self._docopyToNewFolder
            done = self._openSelected(open=False, silent=True)
            if done:
                self._docopyToNewFolder()
            
    def _docopyToNewFolder(self):
        self.setEnabled(True)
        f = self._tempF
        m = self.selectionModel()
        for index in m.selectedRows():
            y = index.row()
            path = self._path2(y)
            self._root.join(path).copy(PathStr(f).join(path.basename()))
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(f))
        self._downloadDone = self._downloadDone_backup
        del self._tempF
        del self._downloadDone_backup

    def _openFolders(self):
        m = self.selectionModel()
        for index in m.selectedRows():
            y = index.row()
            path = self._path2(y)
            fullpath = self._root.join(path).dirname()
            QtGui.QDesktopServices.openUrl(
                QtCore.QUrl.fromLocalFile(fullpath))

    def _path2(self, y):
        pp = []
        for x in range(self._n + 1):
            txt = self.item(y, x).text()
            if txt:
                pp.append(txt)
        return self.pathJoin(pp)

    def _openSelected(self, open=True, silent=False):  # TODO: rename
        '''
        returns Flase if is downloading and True is is ready
        '''
        toDownload, downIndices = [], []

        def openFile(path):
            if open:
                fullpath = self._root.join(path)
                self.fnOpen(fullpath)

        def fileVerified(path):
            # check signature of local file, if cannot be verified, download again
            if self.fnVerify is None:
                return True
            return self.fnVerify(path)

        def addDownload(path, y): 
            toDownload.append(path)
            downIndices.append(y)
            
        QQ = QtWidgets.QMessageBox
        
        m = self.selectionModel()
        for index in m.selectedRows():
            y = index.row()
            path = self._path2(y)
            color = self.item(y, 0).foreground()
            if color == self.COL_OUTDATED:  # file exists but is outdated
                if silent:
                    ret = QQ.Yes
                else:
                    m.select(index, m.ClearAndSelect | m.Rows)
                    self.scrollTo(index)
                    msgBox = QQ()
                    msgBox.setWindowTitle('Open file...')
                    msgBox.setText("The file on your PC is out of date.")
                    msgBox.setInformativeText(
                        "Download latest version from server?")
                    msgBox.setStandardButtons(QQ.Yes | QQ.No)
                    msgBox.setDefaultButton(QQ.Yes)
                    ret = msgBox.exec_()
                if ret == QQ.Yes or not fileVerified(path):
                    addDownload(path, y)
                else:
                    openFile(path)
                    
            elif color == self.COL_NOTEXISTANT:  # no local file
                addDownload(path, y)
            else:  # exists and is up-to-date
                if not fileVerified(path):
                    addDownload(path, y)
                else:
                    openFile(path)
                
        if toDownload:
            self._download(toDownload, downIndices, open)
            return False
        return True

    def sync(self):
        toDownload, downIndices = [], []
        for y in range(self.rowCount()):
            path = self._path2(y)
            col = self.item(y, 0).foreground()
            if col in (self.COL_OUTDATED, self.COL_NOTEXISTANT):
                toDownload.append(path)
                downIndices.append(y)
        if toDownload:
            self._download(toDownload, downIndices, False)

    def _download(self, toDownload, downIndices, openLater=True):
        self.setEnabled(False)
#         self.setDynamic(False)
        self._toDownload = toDownload
        self.downIndices = downIndices
        self._openLater = openLater
        self.fnDownload(toDownload, self._root, self._downloadDone)

    def rowColor(self, row, color):
        for x in range(self.columnCount()):
            self.item(row, x).setForeground(color)

    def _downloadDone(self):
        self.setEnabled(True)
        for path, y in zip(self._toDownload, self.downIndices):
            self.rowColor(y, QtCore.Qt.black)
            if self._openLater:
                self.fnOpen(self._root.join(path))

    def _sort(self):
        super()._sort()
        # set color depending on local and server file date:
        for row in range(self.rowCount()):
            localdate = self.item(row, self._n + 1).text()
            serverdate = self.item(row, self._n + 2).text()
            if localdate == '':
                color = self.COL_NOTEXISTANT
            elif localdate >= serverdate:
                color = QtCore.Qt.black
            else:
                color = self.COL_OUTDATED
            self.rowColor(row, color)

    def stats(self):
        nlocal, nserver, noutdated = 0, 0, 0
        slocal, sserver, soutdated = 0, 0, 0
        for row in range(self.rowCount()):
            itemSize = self.item(row, self._n + 3)
            size = fs.toBytes(itemSize.text())

            if itemSize.foreground() == self.COL_OUTDATED:
                noutdated += 1
                soutdated += size
            elif itemSize.foreground() == self.COL_NOTEXISTANT:
                nserver += 1
                sserver += size
            else:  # itemSize.foreground() == QtCore.Qt.black:
                nlocal += 1
                slocal += size
        return (nlocal, nserver, noutdated,
                fs.toStr(slocal), fs.toStr(sserver), fs.toStr(soutdated))

    def _findFile(self, ss):
        c = self.columnCount() - 3
        for y in range(self.rowCount()):
            found = True
            for x in range(len(ss)):
                t = self.item(y, x).text()
                if t == '':
                    t = self.item(y, self.col(c - 1)).text()
                if t != ss[x]:
                    found = False
                    break
            if found:
                return y

    def updateServerFiles(self, serverfiles=None):
        if serverfiles is None:
            serverfiles = self._serverfiles
        self._serverfiles = serverfiles
        ccc = self.columnCount()
        cc = ccc - 3
        changed = False
        for f, date, size in serverfiles:
            ss = self.pathSplit(f)
            
            date = dateStr(float(date))

            row = self._findFile(ss)
            if row is None:
                # no local file exist -  add new row:
                changed = True
                row = self.rowCount()
                self.setRowCount(row + 1)
                newss = ss[:-1]  # remove file size
                if len(ss) < cc:
                    newss.extend([''] * (cc - len(ss)))
                newss.extend((ss[-1], '', date, size))
                for x, si in enumerate(newss):
                    item = QtWidgets.QTableWidgetItem()
                    item.setText(si)
                    self.setItem(row, self.col(x), item)
            else:
                # add server date in found row
                self.item(row, self._n + 2).setText(date)

        if changed:
            self._sort()

    def _pathToData(self, rootpath):
        '''returns 2d array of all files in [rootpath], splitted by folder'''
        self._root = rootpath
        f = list(PathStr(rootpath).nestedFiles(includeroot=False))
        f = [fi for fi in f if not fi.isHidden()]
        data = [self.pathSplit(fi) for fi in f]
        dates = [dateStr(rootpath.join(fi).date()) for fi in f]
        sizes = [fs.toStr(rootpath.join(fi).size()) for fi in f]
        # transform list of lists into array:
#         lmax = max([len(d) for d in data])
        data2 = np.zeros(shape=(len(data), self.columnCount()),
                         dtype="<U%i" % self.STRING_LEN)

        pathindices = np.array([self.col(ni) for ni in range(self._n)])
        fileindex = self.col(self._n)
        sizeindex = self.col(self._n + 3)
        dateindex = self.col(self._n + 1)
        for (dd, d2, date, size) in zip(data, data2, dates, sizes):
            #             if 'DATA' in dd:
            #                 print(dd)
            d2[pathindices[:len(dd) - 1]] = dd[:-1]
            d2[fileindex] = dd[-1]
            d2[sizeindex] = size
            d2[dateindex] = date
        return data2

    def mousePressEvent(self, event):
        '''open context menu'''
        mouseBtn = event.button()
        if mouseBtn == QtCore.Qt.RightButton:
            self._menu.popup(event.globalPos())
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, *_args, **_kwargs):
        self._openSelected()


if __name__ == '__main__':
    a = np.array([['A', 'B', 'C', 'A', 'B', 'C'],
                  ['1', '1', '2', '2', '3', '1'],
                  ['AA', 'BB', 'cc', 'dd', 'ee', 'ff']])

    import sys
    #######################
    # temporary fix: app crack doesnt through exception
    # https://stackoverflow.com/questions/38020020/pyqt5-app-exits-on-error-where-pyqt4-app-would-not
    sys.excepthook = lambda t, v, b: sys.__excepthook__(t, v, b)
    #######################
    app = QtWidgets.QApplication([])
#     w = ImageTable(a.T, ['Current', 'Date', 'Module', 'Type'])
    w = FileTableView(
        ['Module', 'Current', 'Measurement'], None, None)
    w.setLocalPath(
        PathStr(r'D:\Programming\git\dAServer\dAServer\dAServer\MEDIA\karl\processed'))

    w.show()
    app.exec_()
