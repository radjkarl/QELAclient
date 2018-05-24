import numpy as np
from datetime import datetime
from PyQt5 import QtWidgets, QtCore, QtGui

from fancytools.utils import json2 as json
from fancytools.os.PathStr import PathStr

from imgProcessor.utils.metaData import metaData

# local
from client.widgets.GridEditor import GridEditorDialog
from client.parsePath import CAT_FUNCTIONS, parsePath, toRow
from client.widgets.base.Table import Table

MATRIX_HEADER = ['Path',
                  "Measurement name",
                 "Module ID", 'Current [A]', 'Date', 'Exposure time [s]',
                 'ISO(Gain)', 'f-number', 'Options']
MATRIX_HEADER_WIDTH = [335, 120,
                       # 57,
                        80, 70, 110, 100, 64, 62]
MANDATORY_COLS = [2, 3, 4]
DELIMITER = ',\t'


class _OnlyIntDelegate(QtWidgets.QItemDelegate):

    def createEditor(self, parent, *_args, **_kwargs):
        le = QtWidgets.QLineEdit(parent)
        v = QtGui.QIntValidator(0, 10000, le)
        le.setValidator(v)
        return le


class _OnlyNumberDelegate(QtWidgets.QItemDelegate):

    def createEditor(self, parent, *_args, **_kwargs):
        le = QtWidgets.QLineEdit(parent)
        v = QtGui.QDoubleValidator(0., 100000., 6)
        le.setValidator(v)
        return le


class _OnlyDateDelegate(QtWidgets.QItemDelegate):

    def createEditor(self, parent, *_args, **_kwargs):
        le = QtWidgets.QDateTimeEdit(parent)
        le.setDisplayFormat("yyyy/MM/dd HH:mm:ss")
        le.setDateTime(QtCore.QDateTime.currentDateTime())
        return le

    def setModelData(self, editor, model, index): 
        editor.interpretText()  # needed, otherwise jumps to am/pm, depending on locale
        model.setData(index, editor.text(), QtCore.Qt.EditRole)


class ImageTable(Table):
    filled = QtCore.pyqtSignal()  # whether to modify contents 
    sigIsEmpty = QtCore.pyqtSignal()

    def __init__(self, imgTab):
        super().__init__(1, len(MATRIX_HEADER))  # int rows, int columns

        self.cellDoubleClicked.connect(self._cellDoubleClicked)
        self.currentCellChanged.connect(self._showPreview)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

        self.setTextElideMode(QtCore.Qt.ElideLeft)
        self.itemChanged.connect(self._updateRowNumberColor)

        # draw top header frame :
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setDefaultAlignment(QtCore.Qt.AlignLeft)
        header.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Plain)
        header.setLineWidth(1)
        self.setHorizontalHeader(header)

        self.setHorizontalHeaderLabels(MATRIX_HEADER)
        for col in MANDATORY_COLS:
            item = self.horizontalHeaderItem(col)
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            self.setHorizontalHeaderItem(col, item)
        for col, tip in {1:'''If left empty: measurement name is set to measurement date. 
In other words: A measurement will be defined as all images taken of one module at the same date'''}.items():
            item = self.horizontalHeaderItem(col)
            item.setToolTip(tip)

        [self.setColumnWidth(n, width)
         for n, width in enumerate(MATRIX_HEADER_WIDTH)]
        self._showOptionsColumn(False)

        self.cbMetaData = imgTab.cbMetaData
        self.gui = imgTab.gui
        self.drawWidget = imgTab.dragW

        self.drawWidget.changed.connect(self.valsFromPath)
        self.filled.connect(self.valsFromPath)
        
        self.threadAddMetadata = None
        self.paths = []

        # need to add to self, otherwise garbage collector removes delegates
        self._delegates = {  # 1: _OnlyIntDelegate(),  # measurement number
                           3: _OnlyNumberDelegate(),  # current
                           4: _OnlyDateDelegate(),  # date
                           5: _OnlyNumberDelegate(),  # exp time
                           6: _OnlyNumberDelegate(),  # iso
                           7: _OnlyNumberDelegate()  # fnumber
                           }  

        for i, d in self._delegates.items():
            self.setItemDelegateForColumn(i, d)

        self.hide()
        self.setRowCount(0)

    def uploadStart(self):
        self.currentCellChanged.disconnect(self._showPreview)
        self._closePreview()
        self.insertColumn(0)
        
    def uploadUpdate(self, index, val):
#         if val != 100:
        # show a progress bar  is every top  table cell that is being uploaded:
        bar = self.cellWidget(index, 0)
        if not bar:
            bar = QtWidgets.QProgressBar()
            self.setCellWidget(index, 0, bar)
            # hide all top rows:
            [self.hideRow(i) for i in range(index)]
            bar.setValue(val)
    
        i, j = index + 1, len(self.paths)
        b = self.gui.progressbar
        b.bar.setValue(100 * i / j)
        b.bar.setFormat("Uploading image %i/%i" % (i, j))

    def uploadDone(self, hide=True):
        self.removeColumn(0)
        if hide:
            self.clearContents()
            self.hide()
        else:
            show()
        self.currentCellChanged.connect(self._showPreview)

    def uploadCancel(self):
        self.removeColumn(0)

        for row in range(self.rowCount()):
            self.showRow(row)

    def _applyForAll(self):
        txt = self.currentItem().text()
        col = self.currentColumn()
        for row in range(self.rowCount()):
            self.item(row, col).setText(txt)

    def _selectAllOfCurrentValue(self):
        txt = self.currentItem().text()
        col = self.currentColumn()
# #         self.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
#         self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        rows = []
        for row in range(self.rowCount()):
            if self.itemText(row, col) == txt:
                rows.append(row)
#                 self.selectRow(row)

        indexes = [self.model().index(r, 0) for r in rows]
        mode = QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows
        [self.selectionModel().select(i, mode) for i in indexes]

#         self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        
    def _invertSelection(self):
        model = self.model()
        for i in range(model.rowCount()):
            for j in range(model.columnCount()):
                ix = model.index(i, j)
                self.selectionModel().select(ix, QtCore.QItemSelectionModel.Toggle)

    def removeRow(self, row):
        self.paths.pop(row)
        super().removeRow(row)
        if not len(self.paths):
            self.sigIsEmpty.emit()
            self._showOptionsColumn(False)

    def clearContents(self):
        for row in range(len(self.paths) - 1, -1, -1):
            super().removeRow(row)
        self.paths = []

    def saveState(self):
        rows = []
        for row in range(self.rowCount()):
            line = []
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if item:
                    line.append(str(item.text()))
                else:
                    line.append(None)
            rows.append(line)
        return rows

    def _closePreview(self):
        try:
            self._tempIconWindow.close()
            del self._tempIconWindow
            self.gui.sigMoved.disconnect(self._prefWinFn)
            self.gui.tabs.currentChanged.disconnect(self._closePreview)
        except AttributeError:
            pass

    def wheelEvent(self, evt):
        '''
        close preview image when mouse wheel is used
        '''
        try:
            self._tempIconWindow.close()
        except AttributeError:
            pass
        super().wheelEvent(evt)

    def _openNextRow(self):
        r = self.currentRow()
        if r < self.rowCount() - 1:
            self.selectRow(r + 1)
            path = self.item(r + 1, 0).text()
            self._open(path)

    def _open(self, path):
        self.gui.openImage(path, prevFn=self._openPrevRow,
                               nextFn=self._openNextRow)

    def _openPrevRow(self):
        r = self.currentRow()
        if r > 0:
            self.selectRow(r - 1)
            path = self.item(r - 1, 0).text()
            self._open(path)

    def _doShowPreview(self, path, row, pixmap):
        if pixmap and row == self.currentRow():
            lab = self._tempIconWindow = QtWidgets.QLabel()

            lab.mouseDoubleClickEvent = lambda _evt, path = path: \
                self._open(path)

            lab.setPixmap(pixmap)
            lab.setWindowFlags(QtCore.Qt.FramelessWindowHint
                               | QtCore.Qt.SubWindow
                               )
            lab.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
            
            p0 = self.mapToGlobal(self.parent().pos())
            p1 = QtCore.QPoint(0,  # -pixmap.size().width(),
                               self.rowViewportPosition(self._Lrow))
#                 del self._Lrow

            self._prefWinFn = lambda p, p1 = p1: lab.move(
                p + p1 + self.mapTo(self.gui, self.parent().pos()))
            
            self.gui.sigMoved.connect(self._prefWinFn)
            self.gui.tabs.currentChanged.connect(self._closePreview)

            lab.move(p0 + p1)

            # if the context menu is vsibile before (right clicked on a row
            # then showing preview will hide it again
            # we dont want this - we make menu visibe afterwards
            try:
                menu_visible = self._menu.isVisible()
            except AttributeError:
                menu_visible = False

            lab.show()

            if menu_visible:
                self._menu.setVisible(True)

    def _showPreview(self, row, col):
        self._closePreview()
        # show an image preview
        if col == 0:
            r = self.selectedRanges()
            # check whether only one cell (and not whole row) selected:
            if r and r[0].rowCount() == 1 and r[0].columnCount() == 1:
                path = self.item(row, col).text()
                self._Lrow = row
                # load image in thread to not block GUI:
                self._L = _LoadPreviewThread(path, row)
                self._L.sigDone.connect(self._doShowPreview)
                self._L.start()

    def _cellDoubleClicked(self, row, col):
        if col == 0:
            path = self.item(row, col).text()
            self._open(path)

    def hasEmptyCells(self, cols=None, select=True) -> bool:
        '''
        returns whether table contains empty cells

        if <select> == True: select all empty cells
        '''
        if cols is None:
            cols = range(1, self.columnCount())
        has_empty = False
        for row in range(self.rowCount()):
            if not self.isRowHidden(row):
                for col in cols:
                    if not self.isColumnHidden(col):
                        item = self.item(row, col)
                        if not item or not item.text():
                            if not select:
                                return True
                            has_empty = True
                            index = self.model().index(row, col)
                            self.selectionModel().select(
                                index, QtCore.QItemSelectionModel.Select)
        return has_empty

    def modules(self):
        '''
        return list of module IDs within table
        '''
        ll = set()
        col = MATRIX_HEADER.index('Module ID')
        for row in range(self.rowCount()):
            item = self.item(row, col)
            if item is not None:
                ll.add(item.text())
        return ll

    def showContextMenu(self, pos):
        self._menu = self.createContextMenu()
        self._menu.addAction(
            "Manual grid detection").triggered.connect(self._manualGridDetection)
        self._menu.addAction("Invert selection").triggered.connect(self._invertSelection)
        
        m = self._menu.addMenu("Current value")  
        m.addAction("Apply to all").triggered.connect(self._applyForAll)
        m.addAction("Select all").triggered.connect(self._selectAllOfCurrentValue)

        self._menu.popup(QtGui.QCursor.pos())

    def setReadOnly(self, readonly):
        if readonly:
            tr = QtWidgets.QAbstractItemView.NoEditTriggers
            self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
            col = QtGui.QColor(QtCore.Qt.lightGray)
            for r, c in self.iterInd():
                self.setCell(r, c).setBackground(col)
        else:
            tr = QtWidgets.QAbstractItemView.AllEditTriggers 
            self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            col = QtWidgets.QTableWidgetItem().background()  # QtGui.QColor(QtCore.Qt.white)
            for r, c in self.iterInd():
                self.setCell(r, c).setBackground(col)
        self.setEditTriggers(tr)

    def iterInd(self):
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                yield row, col

    def _manualGridDetection(self):
        row = self.currentRow()

        self._gridEditor = g = GridEditorDialog(self.paths[row])
        # move:
        p0 = self.mapToGlobal(self.parent().pos())
        p0.setY(p0.y() + self.rowViewportPosition(row + 1))
        p0.setX(p0.x() + self.columnViewportPosition(2))
        g.move(p0)

        g.exec_()

        if g.result() == g.Accepted:
            row = self.currentRow()
            col = len(MATRIX_HEADER) - 1
            self.setCell(row, col, json.dumps(g.values))
            self._showOptionsColumn(True)

    def toCSVStr(self, local=True):
        '''
        local ... whether csv str contains local file paths
               set to False t anonymize paths to NUMBER.FTYPE 
        returns:
            local=True:
                str, paths
            local=False
                str,  new_paths
        '''
        out = ''
        new_paths = []
        for row in range(self.rowCount()):
            # only same image index and ftype to protect the clients
            # data"
            path = self.paths[row]
            if local:
                rowl = [path]
            else:
                new_path = '%i.%s' % (row, path.filetype())
                new_paths.append(new_path)
                rowl = [new_path]
            for col in range(1, len(MATRIX_HEADER)):
                rowl.append(self.itemText(row, col))
            rowl.append(str(path.size()))
            line = DELIMITER.join(rowl)
            if line[-1] != '\n':
                line += '\n'
            out += line
        # remove last \n:
        if out[-1] == '\n':
            out = out[:-1]
        if not local:
            return out, new_paths
        return out, self.paths

    def fillFromFile(self, path, appendRows=False):
        with open(path, 'r', encoding='utf-8-sig') as f:
            # using <encoding='utf-8-sig'> to prevent byte order mark (BOM)
            # which is the odd first sign for csv docs saved by excel
            lines = f.read().splitlines()
            if DELIMITER not in lines[0]:
                # csv not generated by QELA but rather by excel
                lines = [line.split(',')
                         for line in lines]
            else:
                lines = [line.split(DELIMITER)
                         for line in lines]                
        return self.fillFromState(lines, appendRows)

    def fillFromState(self, lines, appendRows=False):
        self._allowModelToModifyCells = False

        if appendRows:
            row0 = self.rowCount()
        else:
            row0 = 0
            self.clearContents()
            self.paths = []
        nrows = row0 + len(lines)
        self.setRowCount(nrows)
        self._new_rows = []
        for row, line in enumerate(lines):

            row += row0
            for col, txt in enumerate(line):
                if txt != '':
                    self.setCell(row, col, txt)
            item = self.item(row, 0)
            if len(line) and item:
                self.paths.append(PathStr(item.text()))
                self._setPathItem(row)
                self._setRowItem(row)
                self._new_rows.append(row)
            else:
                nrows -= 1
            
        self.drawWidget.setExamplePath(self.paths[0])
        self.setRowCount(nrows)
        self._checkShowOptionsColumn()
        self._new_paths = self.paths[row0:]
        self.filled.emit()

    def _checkShowOptionsColumn(self):
        hasOptions = False
        c = len(MATRIX_HEADER) - 1
        for row in range(self.rowCount()):
            item = self.item(row, c)
            if item and item.text():
                # TODO: this check is only needed because csv reading incl.
                # last sign currently. remove
                if item.text() != '\n':
                    hasOptions = True
                    break
        self._showOptionsColumn(hasOptions)

    def _showOptionsColumn(self, show):
        c = len(MATRIX_HEADER) - 1
        if show:
            # make sure whole options column is readonly:
            for row in range(self.rowCount()):
                item = self.setCell(row, c)
                self.mkItemReadonly(item)
        
        self.setColumnHidden(c, not show)  # show/hide options

    def _setRowItem(self, row):
        # for colored row indices:
        rowitem = QtWidgets.QTableWidgetItem()
        # previous row item number:
        if row == 0:
            prev = 0
        else:
            item = self.verticalHeaderItem(row - 1)
            if item:
                prev = int(item.text())
            else:
                prev = row - 1
        rowitem.setText(str(prev + 1))
        self.setVerticalHeaderItem(row, rowitem)

    def fillFromPaths(self, paths):
        '''
        paths ... [path/to/img.png, ...]
        '''
        self.show()
        self._allowModelToModifyCells = True
        self._new_paths = paths
        row0 = len(self.paths)
        self.setRowCount(len(paths) + row0)
        self.drawWidget.setExamplePath(paths[0])
        # <<<
        # adds ...
        # - path to FIRST ROWfile
        # - change date
        # row index
        offs = len(self.paths)
        self._new_rows = []
        for r, p in enumerate(self._new_paths):
            if p in self.paths:
                continue  # duplicate found - ignore
            row = r + offs
            # path[column 0] as read-only and underlined:
            self.paths.append(p)
            self._setPathItem(row, p)
            self._setRowItem(row)

            self._new_rows.append(row)
        # >>>

        if self.cbMetaData.isChecked():
            self.addMetaData()
        else:
            self.filled.emit()

    def isEmpty(self):
        return len(self.paths) == 0

    def checkValid(self):
        optional_cols = list(range(1, self.columnCount()))
        optional_cols = [c for c in optional_cols if not c in MANDATORY_COLS]
        
        if self.hasEmptyCells(MANDATORY_COLS):
            QtWidgets.QMessageBox.critical(self, "Table has empty cells",
                             "Please fill out all mandatory cells.",
                             QtWidgets.QMessageBox.Ok)
            return False
        
        if self.hasEmptyCells(optional_cols):
            msg = QtWidgets.QMessageBox.warning(self, "Table has empty cells",
                             """It is recommended to fill every cell. Continue?<br>
Missing data is treated as follows:<br><br>
<b>Measurement name:</b><br>
Is is assumed that all images taken of the same module (ID) <br>
within one day belong to the same measurement.<br><br>
<b>Exposure time, ISO, fnumber:</b><br>
Values are set to 1 <br>
No exposure value correction can be executed and camera calibration <br>
might use false parapeters.""",
                             QtWidgets.QMessageBox.Ok | 
                             QtWidgets.QMessageBox.Cancel)
            if msg == QtWidgets.QMessageBox.Cancel:
                return False
        return True

    def valsFromPath(self): 
        colDate = MATRIX_HEADER.index('Date') 
        for row in range(self.rowCount()):  
            if self._allowModelToModifyCells:
                path = PathStr(self.item(row, 0).text())
                _success, entries = self.drawWidget.model(path)

                for col, e in enumerate(entries):
                    col += 1
#                     if e == '':
#                         item = self.item(row, col)
#                         if hasattr(item, 'metaText'):
#                             e = self.item(row, col).metaText
                    if e != '':
                        self.setCell(row, col, str(e))
                # add date from file date is not already given:
                if not self.itemText(row, colDate):
                    self.setCell(row, colDate, datetime.fromtimestamp(
                        path.date()).strftime('%Y/%m/%d %H:%M:%S'))
#             self._updateRowNumberColor(row)
            
    def _updateRowNumberColor(self, item):
        row = item.row()
        ncol = self.columnCount() - 1  # ignore the options column
        # color row index number:
        # check if whole row contains data:
        if '' not in (self.itemText(row, c) for c in range(ncol)):
            color = QtCore.Qt.darkGreen
        elif '' not in (self.itemText(row, c) for c in MANDATORY_COLS):
            color = QtCore.Qt.darkYellow
        else:
            color = QtCore.Qt.red
        rowitem = self.verticalHeaderItem(row)
        if rowitem:
            rowitem.setForeground(color)
            self.setVerticalHeaderItem(row, rowitem)

    def itemText(self, row, col):
        item = self.item(row, col)
        if item is None:
            return ''
        return item.text()

    def mkItemReadonly(self, item):
        flags = item.flags()
        flags |= QtCore.Qt.ItemIsSelectable
        flags &= ~QtCore.Qt.ItemIsEditable  # reset/clear the flag
        item.setFlags(flags)

    def _setPathItem(self, row, path=None):
        item = self.setCell(row, 0, path)
        item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.mkItemReadonly(item)
        f = item.font()
        f.setUnderline(True)
        item.setFont(f)

    def addMetaData(self):
        self.threadAddMetadata = _ProcessThread(self._new_rows, self._new_paths)
        self.threadAddMetadata.rowDone.connect(self._fillRow)
        self.threadAddMetadata.finished.connect(self._fillFinished)

        self._b = self.gui.addTemporaryProcessBar()
        self._b.setColor('darkgreen')
        self._b.setCancel(self.threadAddMetadata.kill)
        self._b.show()

        self.threadAddMetadata.start()

    def _fillRow(self, progress, row, meta):
        b = self._b
        b.bar.setValue(progress)
        b.bar.setFormat(
            "Reading image meta data %s" % int(progress) + '%')
        for i, t in enumerate(meta):
            self.setCell(row, 4 + i, t)
#             item.metaText = t

    def _fillFinished(self):
        self.gui.removeTemporaryProcessBar(self._b)
        self.filled.emit()


class DragWidget(QtWidgets.QGroupBox):
    '''
    HEADER: fields:[opt1,opt2...]
    row1: PATH      / TO       / FIRST / FILE.XYZ
    row2: [label1],  [label2] <-- drag-able
    '''
    changed = QtCore.pyqtSignal()
    N_LAST_FOLDERS = 5

    def __init__(self):
        super(). __init__('Analyze file path...')
        self.setAcceptDrops(True)
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                           QtWidgets.QSizePolicy.Maximum)
        self.hide()

        l0 = QtWidgets.QHBoxLayout()
        self.setLayout(l0)

        lleft = QtWidgets.QVBoxLayout()
        lright = QtWidgets.QVBoxLayout()

        l0.addLayout(lleft, stretch=0)
        l0.addLayout(lright, stretch=1)

#         lleft.addWidget(QtWidgets.QLabel("Path contains:    "))
        lleft.addWidget(QtWidgets.QLabel("Example path:"))

        self.btn = QtWidgets.QPushButton("Blocks:")
        menu = QtWidgets.QMenu()
        menu.setToolTipsVisible(True)

        a = menu.addAction('<INDIVIDUAL>')
        a.setToolTip(parsePath.__doc__)
        a.triggered.connect(self._addParsePathLabel)

        for k in CAT_FUNCTIONS.keys():
            a = menu.addAction(k)
            a.triggered.connect(lambda _checked, k=k:
                                self._addLabel(_RemovableLabel(self._lGrid, k)))
        self.btn.setMenu(menu)

        lleft.addWidget(self.btn) 

        ll = self._lGrid = QtWidgets.QGridLayout()
        lright.addLayout(self._lGrid)
        lright.addStretch(1)
        for i in range(self.N_LAST_FOLDERS):

            sep = QtWidgets.QLabel(self)
            sep.setText('/')
            sep.setEnabled(False)
            ll.addWidget(sep, 0, 2 * i)

            lab = QtWidgets.QLabel(self)
            # lab.setText('')
            lab.setEnabled(False)

            ll.addWidget(lab, 0, (2 * i) + 1)

    def saveState(self):
        out = []
        for i in range(self.N_LAST_FOLDERS):
            item = self._lGrid.itemAtPosition(1, (2 * i) + 1)
            if item:
                out.append(item.widget().text())
            else:
                out.append(None)
        return out

    def restoreState(self, state):
        for i, s in enumerate(state):
            if s is not None:
                if s in CAT_FUNCTIONS.keys():
                    label = _RemovableLabel(self._lGrid, s)
                else:
                    label = _LabelParsePath(self._lGrid, s)
                self._lGrid.addWidget(label, 1, 2 * i + 1)

    def _addParsePathLabel(self):
        lab = _LabelParsePath(self._lGrid, "#N_#n_")
        lab.setToolTip(parsePath.__doc__)
        lab._editor.setToolTip(parsePath.__doc__)
        lab._editor.editingFinished.connect(self.changed.emit)
        self._addLabel(lab)

    def setExamplePath(self, path):
        #         self.show()
        for i, fold in enumerate(path.splitNames()[-self.N_LAST_FOLDERS:]):
            w = self._lGrid.itemAtPosition(0, 2 * i + 1).widget()
            w.setText(fold)

    def _addLabel(self, label):
        ll = self._lGrid
        # find empty space:
        for i in range(ll.columnCount() // 2):
            if not ll.itemAtPosition(1, 2 * i + 1):
                ll.addWidget(label, 1, 2 * i + 1)
                label.show()
                break
        self.changed.emit()

    def activeLabels(self):
        labels = [self._lGrid.itemAtPosition(1, col)
                  for col in range(self._lGrid.columnCount())]
        return [item.widget() for item in labels if item]

    def mousePressEvent(self, event):

        child = self.childAt(event.pos())
        if not child or child not in self.activeLabels():
            self._curChild = None
            return

        self._offs = event.pos().x() - child.pos().x()

        self._curChild = child

        # calc label gap positions:
        la = self._lGrid
        self._poss = []
        for i in range(la.columnCount() // 2):
            lab = la.itemAtPosition(0, 2 * i + 1)
            self._poss.append(lab.geometry().right())

        event.accept()

    def mouseMoveEvent(self, event):
        if not self._curChild:
            return
        # move only in x
        y = self._curChild.pos().y()
        self._curChild.move(event.pos().x() - self._offs, y)

    def labelIndex(self, label):
        return self._lGrid.getItemPosition(
            self._lGrid.indexOf(label))[1]

    def mouseReleaseEvent(self, event):
        if not self._curChild:
            return
        pos = event.pos().x() + self._curChild.rect().center().x()
        i = np.argmin([abs(p - pos) for p in self._poss])
        #
        pos = (2 * i) + 1

        item = self._lGrid.itemAtPosition(1, pos)

        ind = self.labelIndex(self._curChild)
        if item:
            # swap position
            self._lGrid.addWidget(item.widget(), 1, ind)

        self._lGrid.addWidget(self._curChild, 1, pos)
        self._lGrid.update()

        if ind != pos:
            self.changed.emit()

    def model(self, path):
        '''
        depending on adjusted label positions,
        split given path into MATRIX row
        '''
        names = path.splitNames()[-self.N_LAST_FOLDERS:]
        names[-1] = PathStr(names[-1]).rmFileType()

        out = [''] * (len(MATRIX_HEADER) - 1)
        success = True
        for i, n in enumerate(names):
            item = self._lGrid.itemAtPosition(1, (2 * i) + 1)
            if item:
                txt = item.widget().text()
                try:
                    fn = CAT_FUNCTIONS[txt]
                    fn(out, n)
                except KeyError:
                    toRow(out, parsePath(n, txt))
                except IndexError:
                    pass

        return success, out


class _RemovableLabel(QtWidgets.QLabel):

    def __init__(self, layout, txt):
        super(). __init__(txt)
        self._lay = layout
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showMenu)

        self.setFrameStyle(QtWidgets.QFrame.Sunken | 
                           QtWidgets.QFrame.StyledPanel)

    def remove(self):
        self._lay.removeWidget(self)
        self.close()

    def showMenu(self, evt):
        m = QtWidgets.QMenu()
        m.addAction('Remove').triggered.connect(self.remove)
        m.exec_(self.mapToGlobal(evt))


class _LabelParsePath(_RemovableLabel):
    '''
    Dummy placeholder label within dragWidget
    Can be modified at double click
    remove option is shown at right click
    '''

    def __init__(self, layout, txt):
        super(). __init__(layout, txt)

        p = self.palette()
        p.setColor(QtGui.QPalette.WindowText, QtGui.QColor('gray'))
        self.setPalette(p)

        self._editor = QtWidgets.QLineEdit(self)
        self._editor.setWindowFlags(QtCore.Qt.Popup)
#         self._editor.setFocusProxy(self)
        self._editor.editingFinished.connect(self.handleEditingFinished)
        self._editor.installEventFilter(self)

    def eventFilter(self, widget, event):
        if ((event.type() == QtCore.QEvent.MouseButtonPress and
             not self._editor.geometry().contains(event.globalPos())) or
            (event.type() == QtCore.QEvent.KeyPress and
             event.key() == QtCore.Qt.Key_Escape)):
            self._editor.hide()
            return True
        return super().eventFilter(widget, event)

    def mouseDoubleClickEvent(self, _evt):
        self._editor.setText(self.text())
        self._editor.move(self.parent().mapToGlobal(self.pos()))
        self._editor.show()

    def handleEditingFinished(self):
        self._editor.hide()
        self.setText(self._editor.text())


class _LoadPreviewThread(QtCore.QThread):
    sigDone = QtCore.pyqtSignal(str, int, QtGui.QPixmap)  # , QtGui.QIcon)

    def __init__(self, path, row):
        QtCore.QThread.__init__(self)
        self.path = path
        self.row = row

    def run(self):
        pm = QtGui.QIcon(self.path).pixmap(100, 100)
        self.sigDone.emit(self.path, self.row, pm)


class _ProcessThread(QtCore.QThread):
    '''
    Thread to be used in tool.activate in order not to block
    the gui
    '''
    rowDone = QtCore.pyqtSignal(object, object, object)

    def __init__(self, rows, paths):
        QtCore.QThread.__init__(self)
        self.rows = rows
        self.paths = paths

    def kill(self):
        self.terminate()

    def run(self):

        for i, (row, path) in enumerate(zip(self.rows, self.paths)):
            # try to read metadata:
            out = metaData(path)

            progress = (i + 1) / len(self.paths) * 100  # %
            self.rowDone.emit(progress, row, out)


if __name__ == '__main__':
    import sys
    #######################
    # temporary fix: app crack doesnt through exception
    # https://stackoverflow.com/questions/38020020/pyqt5-app-exits-on-error-where-pyqt4-app-would-not
    sys.excepthook = lambda t, v, b: sys.__excepthook__(t, v, b)
    #######################
    app = QtWidgets.QApplication([])
    w = _TableBaseCopyPaste(10, 10)

#     w.restore(w.config())

    w.show()
    app.exec_()
    
