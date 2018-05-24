from PyQt5 import QtWidgets, QtGui

from client.widgets._Base import QMenu


class Table(QtWidgets.QTableWidget):
    '''
    a simple table base enabeling ...
    delete (only,  multiple items)
    copy/paste from clipboard (excel) of from same table
    '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lastCellRange = None

    def keyPressEvent(self, evt):
        if evt.matches(QtGui.QKeySequence.Delete):
            self.deleteSelection()
        elif evt.matches(QtGui.QKeySequence.SelectAll):
            self.selectAll()
        elif evt.matches(QtGui.QKeySequence.Copy):
            self.copyToClipboard()
        elif evt.matches(QtGui.QKeySequence.Paste):
            self.pasteFromClipboard()
        else:
            super().keyPressEvent(evt)

    def createContextMenu(self):
        m = QMenu()
        m.addAction("Remove row(s)").triggered.connect(self.removeSelectedRows)
        m.addAction("Select all").triggered.connect(self.selectAll)
        return m

    def deleteSelection(self):
        n = self.visibleColumnCount()
        for ran in self.selectedRanges():

            if ran.columnCount() >= n:
                self._removeRowFromSelection(ran)
            else:
                for row in range(ran.topRow(), ran.bottomRow() + 1):
                    for col in range(ran.leftColumn(), ran.rightColumn() + 1):
                        item = self.item(row, col)
                        if  item:
                            item.setText('')           

    def visibleColumnCount(self):
        c = self.columnCount()
        for col in range(c):
            if self.isColumnHidden(col):
                c -= 1
        return c

    def removeSelectedRows(self):
        for ran in self.selectedRanges():
            self._removeRowFromSelection(ran)

    def _removeRowFromSelection(self, ran):
            for row in range(ran.bottomRow(), ran.topRow() - 1, -1):
                self.removeRow(row)
                
    def pasteFromClipboard(self):
        if self._lastCellRange is None:
            txt = QtWidgets.QApplication.clipboard().text()
            self.pasteTable(self.strToTable(txt),
                            self.currentRow(),
                            self.currentColumn())
            QtWidgets.QApplication.clipboard().clear()
            
        else:
            self._pasteFromRange(self._lastCellRange,
                            self.currentRow(),
                            self.currentColumn())            
        
            self._lastCellRange = None

    def setCell(self, row, col, txt=None):
        item = self.item(row, col)
        if item is None:
            item = QtWidgets.QTableWidgetItem()
        if txt is not None:
            item.setText(txt)
        self.setItem(row, col, item)
        return item

    def strToTable(self, text, separator='\t'):
        table = text.split('\n')
        n = 0
        while n < len(table):
            sline = table[n].split(separator)
            if sline != ['']:
                table[n] = sline
            else:
                table.pop(n)
                n -= 1
            n += 1
        return table

    def _pasteFromRange(self, rang, startRow, startCol):
        for col in range(rang.leftColumn(), rang.rightColumn() + 1):
            for row in range(rang.topRow(), rang.bottomRow() + 1):
                item = self.item(row, col)
                if item:
                    self.setCell(row + startRow, col + startCol, item.text())

    def pasteTable(self, table, startRow=0, startCol=0):
        nrows = len(table)
        if nrows:
            ncols = len(table[0])
            if nrows > self.rowCount():
                self.setRowCount(nrows)
            if ncols > self.columnCount():
                self.setColumnCount(ncols)
    
            for row, line in enumerate(table):
                for col, text in enumerate(line):
                    r, c = row + startRow, col + startCol
                    self.setCell(r, c, str(text))

    def copyToClipboard(self, cellrange=None):
        if cellrange is None:
            cellrange = self.selectedRanges()[0]
        self._lastCellRange = cellrange 
        # deselect all other ranges, to show shat only the first one will
        # copied
        for otherRange in self.selectedRanges()[1:]:
            self.setRangeSelected(otherRange, False)

        text = self.toStr(cellrange)
        QtWidgets.QApplication.clipboard().setText(text)

    def toStr(self, cellrange=None):
        text = ''
        firstCol, lastCol, firstRow, lastRow = self._getRange(cellrange)          
        for row in range(firstRow, lastRow):
            for col in range(firstCol, lastCol):
                item = self.setCell(row, col)
                text += str(item.text())
                if col != lastCol - 1:
                    text += '\t'
            text += '\n'
        return text

    def _getRange(self, cellrange):
        if cellrange is None:
            firstCol = 0
            firstRow = 0
            lastRow = self.rowCount()
            lastCol = self.columnCount()
        else:
            firstCol = cellrange.leftColumn()
            lastCol = firstCol + cellrange.columnCount()
            firstRow = cellrange.leftColumn()
            lastRow = firstRow + cellrange.rowCount()
        return firstCol, lastCol, firstRow, lastRow        

    def toTable(self, cellrange=None):
        firstCol, lastCol, firstRow, lastRow = self._getRange(cellrange) 
        table = []
        for row in range(firstRow, lastRow):
            line = []
            table.append(line)
            for col in range(firstCol, lastCol):  
                item = self.setCell(row, col)
                line.append(str(item.text()))
        return table
