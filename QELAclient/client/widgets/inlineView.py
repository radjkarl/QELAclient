import os
from PyQt5 import QtWidgets, QtGui
from pyqtgraph_karl.imageview.ImageView import ImageView
from fancytools.os.PathStr import PathStr

import client
from client.imread import imread
from imgProcessor.transformations import toGray

# def _prep(V, path):
#     V.setWindowTitle(path)
#     V.setWindowIcon(QtGui.QIcon(client.ICON))
#     V.show()


class InlineView():

    def __init__(self):
        self._last = None

    def __call__(self, path, prevFn=None, nextFn=None):
        ftype = PathStr(path).filetype()
        V = None
        if ftype != 'svg':
            if ftype in QtGui.QImageReader.supportedImageFormats():
                V = InlineView_image
            elif ftype == 'csv':
                V = _CSVviewer
            elif ftype == 'txt':
                V = _Txtviewer
 
        if V is None:
            return os.startfile(path)
        self._prep(V, path, prevFn, nextFn)
        return V

    def _prep(self, V, path, prevFn, nextFn):
        if isinstance(self._last, V):
            V = self._last
            V.new(path)
        else:
            V = V(path)
            self._last = V
        V.setWindowTitle(path)
        V.setWindowIcon(QtGui.QIcon(client.ICON))
        
        if prevFn:
            try:
                V.btnPrev.disconnect()
                V.btnNext.disconnect()
            except Exception:
                pass
            V.btnPrev.clicked.connect(prevFn)
            V.btnNext.clicked.connect(nextFn)
            V.btnPrev.show()
            V.btnNext.show()
        else:
            V.btnPrev.show()
            V.btnNext.show()            
            
        V.show()

# def inlineView(path, prefFn=None, nextFn=None):
#     ftype = PathStr(path).filetype()
#     V = None
#     if ftype != 'svg':
#         if ftype in QtGui.QImageReader.supportedImageFormats():
#             V = InlineView_image(path)
# 
#         elif ftype == 'csv':
#             with open(path, 'r') as f:
#                 data = [line.split(';') for line in f.read().splitlines()]
#             s0 = len(data)
#             s1 = len(data[0])
#             V = QtWidgets.QTableWidget(s1, s0)
#             for irow, row in enumerate(data):
#                 for icol, cell in enumerate(row):
#                     i = QtWidgets.QTableWidgetItem()
#                     i.setText(cell)
#                     V.setItem(irow, icol, i)
#             V.resizeColumnsToContents()
#             V.resizeRowsToContents()
#     
#         elif ftype == 'txt':
#             with open(path, 'r') as f:
#                 V = QtWidgets.QPlainTextEdit(f.read())
#         
#     if V is None:
#         return os.startfile(path)
#     _prep(V, path, prefFn, nextFn)
#     return V


class _InlineBase:

    def __init__(self):
        st = QtWidgets.QApplication.style()

        b0 = self.btnPrev = QtWidgets.QPushButton(self)
        b1 = self.btnNext = QtWidgets.QPushButton(self)
        b0.resize(40, 17)
        b1.resize(40, 17)

#         b0.move(150, 0)
        b1.move(40, 0)
#         print(b0.pos())
        b0.setIcon(st.standardIcon(QtWidgets.QStyle.SP_MediaSeekBackward))
        b1.setIcon(st.standardIcon(QtWidgets.QStyle.SP_MediaSeekForward))


class _Txtviewer(QtWidgets.QPlainTextEdit):

    def __init__(self, path):
        QtWidgets.QPlainTextEdit.__init__(self)
        _InlineBase.__init__(self)

        self.new(path)
        
    def new(self, path):
        with open(path, 'r') as f:    
            self.setPlainText(f.read())

    
class _CSVviewer(QtWidgets.QTableWidget, _InlineBase):

    def __init__(self, path):
        QtWidgets.QTableWidget.__init__(self)
        _InlineBase.__init__(self)
        self.new(path)
        
    def new(self, path):
        with open(path, 'r') as f:
            data = [line.split(';') for line in f.read().splitlines()]
        s0 = len(data)
        s1 = len(data[0])
        
        self.clear()
        self.setRowCount(s1)
        self.setColumnCount(s0)
#         super().__init__(s1, s0)
        for irow, row in enumerate(data):
            for icol, cell in enumerate(row):
                i = QtWidgets.QTableWidgetItem()
                i.setText(cell)
                self.setItem(irow, icol, i)
                
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        

class InlineView_image(ImageView, _InlineBase):
    '''
    an image viewer with zoom on mouse wheel
    and context menu
    '''

    def __init__(self, path):
        ImageView.__init__(self)
        self.ui.roiBtn.hide()        
        self.ui.menuBtn.hide()
        self.btn = QtWidgets.QPushButton(self)
        self.btn.resize(80, 17)
        self.btn.move(80, 0)
        
        self.btn.clicked.connect(self._toggleGray)

        _InlineBase.__init__(self)
        self.new(path)
        
    def new(self, path):
        self.img = imread(path)
        self._toggleGray(forceGray=True)

    def _toggleGray(self, forceGray=False):
        if forceGray or self.image.ndim == 3:
            img = toGray(self.img)
            self.setImage(img)
            if self.img.ndim > 2:
                self.btn.setText('RGB')
            else:
                self.btn.hide()
            self.ui.histogram.show()
        else:
            self.setImage(self.img)
            self.btn.setText('Gray')
            self.ui.histogram.hide()


if __name__ == '__main__':
    from client.Application import Application

    app = Application()

    d = PathStr('../media/help/bg_straylight.jpg')

    i = InlineView()
    i(d, lambda:None, lambda: None)

    app.exec_()
