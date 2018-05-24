# cellAverage and perspective fit functionality is in PerspectiveGridROI
# to reduce import speed and overhead for those cases that dont need those
# functions

import numpy as np

from pyqtgraph_karl.Qt import QtGui, QtCore, QtWidgets
from pyqtgraph_karl.graphicsItems.ROI import Handle


from dataArtist.items.QuadROI import QuadROI


class HH(Handle):

    def __init__(self, fn, *args, pos=(1, 1), parent=None, **kwargs):

        Handle.__init__(self, *args, parent=parent, **kwargs)
        self.roi = parent
        self.pos = pos
        self.fn = fn
        self._update()
        self.roi.sigRegionChanged.connect(self._update)

        self.pen.setWidth(kwargs['pen']['width'])

    def _edgePos(self, w=None):
        # returns handle position
        t = self.roi._homography
        n = self.roi.nCells

        if w is None:
            w = self.roi.width
        p = self.pos
        return t.map(QtCore.QPointF(((p[0] - w[1]) / n[1]),
                                    (p[1] - w[0]) / n[0]))

    def _update(self):

        self.setPos(self._edgePos())

    def mouseDragEvent(self, ev):
        super().mouseDragEvent(ev)
        if ev.button() != QtCore.Qt.LeftButton:
            return
        if ev.isFinish():
            self.roi.stateChangeFinished()

    def movePoint(self, pos, modifiers=QtCore.Qt.KeyboardModifier(), finish=True):
        pos0 = self.roi.mapSceneToParent(pos)
        rpos0 = self.roi.homography().inverted()[0].map(pos0)

        nx, ny = self.roi.nCells
        y, x = -np.clip(rpos0.x(), 0, 1 / ny), -np.clip(rpos0.y(), 0, 1 / nx)

        rpos0.setX(x)
        rpos0.setY(y)

        self.fn(x + (1 / nx), y + (1 / ny))
        self.roi.sigRegionChanged.emit(self.roi)


class PerspectiveGridROI(QuadROI):
    def __init__(self, nCells=(3, 4), nSublines=(0, 0),
                 pos=(0, 0), size=(1, 1), width=(0, 0), **kwargs):
        QuadROI.__init__(self, pos=pos, size=size, removable=True, **kwargs)
        self.nCells = list(nCells)
        self.nSublines = list(nSublines)

        self._shape = None
        self._size = size
        self.width = width
        self.circleOffs = QtCore.QSizeF(0, 0)

        self.homography()

        self._hCellSize = HH(self.setWidth2, self.handleSize, typ='s',
                             pen={'color': 'b', 'width': 3}, parent=self)
        self._hCellShape = HH(self.setCircle, self.handleSize, typ='s', pos=(0.5, 1),
                              pen={'color': 'c', 'width': 3}, parent=self)

    def getMenu(self):
        if self.menu is None:
            menu = super().getMenu()

            for axis, cfn, nc, subfn, nsub in (('X Axis', self.setNCellsX, self.nCells[0],
                                                self.setNSublinesY, self.nSublines[1]),
                                               ('Y Axis', self.setNCellsY, self.nCells[1],
                                                self.setNSublinesX, self.nSublines[0])):
                w = QtWidgets.QWidget()
                lv = QtWidgets.QVBoxLayout()
                w.setLayout(lv)

                lv.addWidget(QtWidgets.QLabel(axis))

                for name, n, fn, minn in (('Cells', nc, cfn, 1), ('Busbars', nsub, subfn, 0)):
                    lh = QtWidgets.QHBoxLayout()
                    lh.addWidget(QtWidgets.QLabel(name))

                    spin = QtWidgets.QSpinBox()
                    spin.setRange(minn, 100)
                    spin.setValue(n)
                    spin.valueChanged.connect(fn)
                    lh.addWidget(spin)

                    lv.addLayout(lh)

                a = QtWidgets.QWidgetAction(self)
                a.setDefaultWidget(w)
                menu.addAction(a)

        return self.menu

    def setCircle(self, _dx, dy):
        n = self.nCells[1]
        o = max(0, 2 * (dy - (0.5 / n)))
        return self.setCircleOffs(QtCore.QSizeF(0, o))

    def setCircleOffs(self, offsSize):
        self.circleOffs = offsSize
        self._shape = None
        self.update()

    def drawCell(self, p, x0, x1, y0, y1, subx, suby):
        w, h = x1 - x0, y1 - y0
        rect = QtCore.QRectF(x0, y0, w, h)
        # rect:
        pp1 = QtGui.QPainterPath()
        pp1.addRect(rect)
        # busbars:
        # TODO: make width variable ... currently fixed to 1e-3
        ps = QtGui.QPainterPath()
        for yi in subx:
            yi = y0 + yi * (y1 - y0)
            ps.addRect(QtCore.QRectF(x0, yi, w, 1e-3))

        for xi in suby:
            xi = x0 + xi * (x1 - x0)
            ps.addRect(QtCore.QRectF(xi, y0, 1e-3, h))

        if not self.circleOffs.isNull():
            # intersect rect with ellipse to create pseudo rect shape:
            # scale rect:
            c = rect.center()
            esize = rect.size() * 2**0.5 - self.circleOffs
            esize.setWidth(max(rect.width(), esize.width()))
            esize.setHeight(max(rect.height(), esize.height()))

            rect.setSize(esize)
            rect.moveCenter(c)

            pp2 = QtGui.QPainterPath()
            pp2.addEllipse(rect)
            pp1 = pp2.intersected(pp1)
            ps = pp2.intersected(ps)
        p.addPath(ps)
        p.addPath(pp1)

    def setWidth2(self, dx, dy):
        n = self.nCells
        return self.setWidth(n[0] * dx, n[1] * dy)

    def setWidth(self, dx, dy):
        self.width = dx, dy
        self._shape = None
        self.update()

    @staticmethod
    def _genSublines(nsublines):
        # IN: number of sublines
        # OUT: distances of sublines within cell
        if not nsublines:
            return []
        h = 1 / nsublines / 2
        return np.linspace(-h, 1 + h, nsublines + 2)[1:-1]

    def shape2(self):
        if self._shape is None:

            subx = self._genSublines(self.nSublines[1])
            suby = self._genSublines(self.nSublines[0])

            wx, wy = self.width[1] / \
                self.nCells[1], self.width[0] / self.nCells[0]
            p = QtGui.QPainterPath()

            p.moveTo(0, 0)
            xx = np.linspace(0, 1, self.nCells[1] + 1)
            yy = np.linspace(0, 1, self.nCells[0] + 1)
            for i, (x0, x1) in enumerate(zip(xx[:-1], xx[1:])):
                for j, (y0, y1) in enumerate(zip(yy[:-1], yy[1:])):
                    # set offset so, that boundary cells go till boundary
                    # and offset only is between cells :
                    if i == 0:  # left
                        wx0 = 0
                        wx1 = wx
                    else:
                        if i == self.nCells[1] - 1:  # right
                            wx1 = 0
                            wx0 = wx
                        else:  # middle
                            wx1 = wx / 2
                            wx0 = wx / 2
                    if j == 0:  # bottom
                        wy0 = 0
                        wy1 = wy
                    else:
                        if j == self.nCells[0] - 1:  # top
                            wy1 = 0
                            wy0 = wy
                        else:  # middle
                            wy1 = wy / 2
                            wy0 = wy / 2

                    self.drawCell(p, x0 + wx0, x1 - wx1, y0 + wy0, y1 - wy1,
                                  subx, suby)

            self._shape = p

        return self._shape

    def homography(self):
        t = QtGui.QTransform()
        poly = QtGui.QPolygonF([QtCore.QPointF(*v) for v in self.vertices()])
        QtGui.QTransform.squareToQuad(poly, t)
        self._homography = t
        return t

    def painterPath(self):
        t = self.homography()
        return t.map(self.shape2())

    def paint(self, p, opt, widget):
        pen = QtGui.QPen(self.currentPen)
        pen.setWidth(pen.width() // 2)
        c = pen.color()
        r, g, b, a = c.getRgb()
        c.setRgb(255 - r, 255 - g, 255 - b)  # invert
        pen.setColor(c)
        p.setPen(pen)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        p.drawPath(self.painterPath())

    def setNCellsX(self, x):
        self.nCells[0] = x
        self._shape = None
        self.update()

    def setNCellsY(self, y):
        self.nCells[1] = y
        self._shape = None
        self.update()

    def vertices(self):
        return np.array([h['item'].pos() for h in self.handles])

    def setNSublines(self, nSublines):
        self.nSublines = list(nSublines)
        self._shape = None
        self.update()

    def setNSublinesY(self, y):
        self.nSublines[1] = y
        self._shape = None
        self.update()

    def setNSublinesX(self, x):
        self.nSublines[0] = x
        self._shape = None
        self.update()

    def setNCells(self, nCells):
        self.nCells = nCells
        self._shape = None
        self.update()

    def setVertices(self, vertices):
        for h, c in zip(self.handles, vertices):
            self.movePoint(h['item'], c)
        self.homography()
        self.sigRegionChanged.emit(self)


# SEE PerspectveGridROI.py for test case
