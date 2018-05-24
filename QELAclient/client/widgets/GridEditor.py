import numpy as np

from PyQt5 import QtWidgets, QtCore, QtGui

import pyqtgraph_karl as pg
from pyqtgraph_karl.imageview.ImageView import ImageView

# from imgProcessor.imgIO import imread

from dataArtist.items.PerspectiveGridROIbase import PerspectiveGridROI as PGROI
# LOCAL
from client.imread import imread
from imgProcessor.transformations import toGray

pg.setConfigOption('foreground', 'k')
pg.setConfigOption('background', 'w')
pg.setConfigOptions(imageAxisOrder='row-major')


class PerspectiveGridROI(PGROI):

    def __init__(self, pen={'color': 'g', 'width': 3}, **kwargs):
        PGROI.__init__(self, pen=pen, **kwargs)
        h = self.handles[0]['item']
        # change color
        h.pen.setColor(QtGui.QColor("red"))
        h.pen.setWidth(2)
        self.removable = False  # hide context menu


class ImageView2(ImageView):

    def __init__(self):

        ImageView.__init__(self, view=pg.PlotItem())
        # hide buttons
        self.ui.roiBtn.hide()
        self.ui.menuBtn.hide()
        # fixed height for time axis:
        self.ui.splitter.setSizes([self.height() - 35, 35])
        self.ui.splitter.setStretchFactor(0, 1)
        # Remove ROI plot:
        self.ui.roiPlot.setMouseEnabled(False, False)
        self.ui.roiPlot.hide()


class GridEditor(QtWidgets.QWidget):
    gridChanged = QtCore.pyqtSignal(str, object)
    verticesChanged = QtCore.pyqtSignal(object)

    def __init__(self, ncells=(10, 6), nsublines=(2, 0), vertices=None):
        super().__init__()

        ll = QtWidgets.QGridLayout()
        ll.setColumnStretch(1, 1)
        self.setLayout(ll)

        self.imageview = ImageView2()

        ll.addWidget(self.imageview, 0, 1)

        labX = QtWidgets.QLabel("Grid:")
        self.edX = QtWidgets.QSpinBox()
        self.edX.setRange(1, 100)
        self.edX.setValue(ncells[0])
        self.edX.valueChanged.connect(self._changedGrid)

        self.edY = QtWidgets.QSpinBox()
        self.edY.setRange(1, 100)
        self.edY.setValue(ncells[1])
        self.edY.valueChanged.connect(self._changedGrid)

        labBB = QtWidgets.QLabel("Busbars:")
        self.edBBX = QtWidgets.QSpinBox()
        self.edBBX.setRange(0, 10)
        self.edBBX.setValue(nsublines[0])
        self.edBBX.valueChanged.connect(self._changedBusbars)

        self.edBBY = QtWidgets.QSpinBox()
        self.edBBY.setRange(0, 10)
        self.edBBY.setValue(nsublines[1])
        self.edBBY.valueChanged.connect(self._changedBusbars)

        self.btnBLcorner = QtWidgets.QPushButton('Rotate 90DEG')
        self.btnBLcorner.setIcon(QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.SP_BrowserReload))
        self.btnBLcorner.clicked.connect(self._changedBLcorner)

        self.bottomLayout = lll = QtWidgets.QGridLayout()
        ll.addLayout(lll, 2, 1)

        lll.addWidget(labX, 0, 2, QtCore.Qt.AlignRight)
        lll.addWidget(self.edX, 0, 3)
        lll.addWidget(self.edY, 0, 4)
        lll.addWidget(labBB, 0, 5, QtCore.Qt.AlignRight)
        lll.addWidget(self.edBBX, 0, 6)
        lll.addWidget(self.edBBY, 0, 7)
        lll.addWidget(self.btnBLcorner, 0, 8)

        w = self.imageview
        self.grid = PerspectiveGridROI(
            nCells=ncells, nSublines=nsublines)
        self.grid.sigRegionChangeFinished.connect(self._changedVertices)
        w.view.vb.addItem(self.grid)

        if vertices is not None:
            self.grid.setVertices(vertices)

    def _changedVertices(self):
        self.verticesChanged.emit(self.grid.vertices())

    def _changedGrid(self):
        x, y = self.edX.value(), self.edY.value()
        self.grid.setNCells((x, y))
        self.gridChanged.emit('grid', [y, x])

    def _changedBusbars(self):
        x, y = (self.edBBX.value(),
                self.edBBY.value())
        self.grid.setNSublines((x, y))
        self.gridChanged.emit('nsublines', [y, x])

    def _changedBLcorner(self):
        vertices = self.grid.vertices()
        vertices = np.roll(vertices, 1, axis=0)
        self.grid.setVertices(vertices)

#         self.cornerChanged.emit()
        self.verticesChanged.emit(vertices)


class GridEditorDialog(QtWidgets.QDialog):

    def __init__(self, imagepath, *args, **kwargs):
        super().__init__()
        self.setWindowTitle('Set grid manual')
        flags = self.windowFlags()
        self.setWindowFlags(flags | QtCore.Qt.WindowMaximizeButtonHint)

        self.editor = GridEditor(*args, **kwargs)
        # set image
        img = toGray(imread(imagepath))  # , 'gray')
        self.editor.imageview.setImage(img)

        if 'vertices' not in kwargs:
            # set vertices
            sy, sx = img.shape[:2]
            px, py = sx * 0.2, sy * 0.2

            self.editor.grid.setVertices(
                np.array([[px, py], [px, sy - py],
                          [sx - px, sy - py], [sx - px, py]]))

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.editor)
        self.setLayout(layout)

        btn_done = QtWidgets.QPushButton("Done")
        btn_done.clicked.connect(self.accept)
        self.editor.bottomLayout.addWidget(btn_done, 0, 0)
        self.values = None

    def accept(self):
        g = self.editor.grid
        self.values = {'grid': g.nCells, 'nsublines': g.nSublines,
                       'vertices': g.vertices()}
        QtWidgets.QDialog.accept(self)


class CompareGridEditor(GridEditor):

    def __init__(self):
        super().__init__()
        self.imageview.view.setTitle('Camera corrected')
        self.imageview2 = ImageView2()
        self.imageview2.view.setTitle('Perspective corrected')
        self.layout().addWidget(self.imageview2, 1, 1)

    def readImg1(self, path):
        img = imread(path)
        self.imageview.setImage(img, autoRange=False)

    def readImg2(self, path):
        img = imread(path)
        self.imageview2.setImage(img, autoRange=False)


if __name__ == '__main__':
    import sys

    #######################
    # temporary fix: app crack doesnt through exception
    # https://stackoverflow.com/questions/38020020/pyqt5-app-exits-on-error-where-pyqt4-app-would-not
    sys.excepthook = lambda t, v, b: sys.__excepthook__(t, v, b)
    #######################
    app = QtWidgets.QApplication([])
    w = GridEditor(vertices=[[0, 0],
                             [0, 10],
                             [10, 10],
                             [10, 0]])

    w.gridChanged.connect(print)
    w.verticesChanged.connect(print)

    w.show()

    w2 = CompareGridEditor()
    w2.show()

    app.exec_()
