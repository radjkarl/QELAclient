'''
Created on 24 May 2018

@author: karl
'''
from PyQt5 import QtWidgets, QtCore


class Tour(QtWidgets.QScrollArea):
    style = '''
            border-style: outset;
            border-width: 2px;
            border-color: red;'''

    def __init__(self, gui, tour_len, fnNext, title=None, fnClose=None):
        super().__init__(gui)
        self.lab = QtWidgets.QLabel()
        self.lab.setWordWrap(True)
        l0 = QtWidgets.QVBoxLayout()
        l0.setContentsMargins(0, 0, 0, 0)
        l0.setSpacing(0)

        self.setLayout(l0)
        self._layHeader = lh = QtWidgets.QHBoxLayout()
        lh.setContentsMargins(0, 0, 0, 0)
        lh.setSpacing(0)
        
        l0.addLayout(lh)
        l0.addWidget(self.lab)
        
#         self.setWidget(self.lab)
        self._tour_len = tour_len
        self._nextFn = fnNext
        self._fnClose = fnClose
        self._offy = 40
        self.index = -1
        btn_width = 22
                
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.gui = gui
        try:
            self.gui.sigResized.connect(self._updatePos)
        except AttributeError:
            pass
        self._updatePos(gui.size())        

        st = QtWidgets.QApplication.style()

        self.btn1 = btn1 = QtWidgets.QPushButton()
        btn1.setIcon(st.standardIcon(QtWidgets.QStyle.SP_MediaSeekBackward))
        btn1.resize(btn_width, btn_width)

        self.btn2 = btn2 = QtWidgets.QPushButton()
        btn2.setIcon(st.standardIcon(QtWidgets.QStyle.SP_MediaSeekForward))
        btn2.move(QtCore.QPoint(btn_width, 0))  # TODO: btn1.size().width() doesnt show actual width ... therefore hard coded at 22 
        btn2.resize(btn_width, btn_width)

        lh.addWidget(btn1)
        lh.addWidget(btn2)
        
        if title:
            lt = QtWidgets.QLabel('<b>%s</b>' % title)
            lt.move(2 * btn_width + 4, 5)
            lh.addWidget(lt)
        lh.addStretch()

        self.btn3 = btn3 = QtWidgets.QPushButton()
        btn3.setIcon(st.standardIcon(QtWidgets.QStyle.SP_DialogCloseButton))
        lh.addWidget(btn3)

        btn1.clicked.connect(lambda: self.next(-1))
        btn2.clicked.connect(lambda: self.next(1))
        btn3.clicked.connect(self._finish)
        btn3.resize(btn_width, btn_width)

        self.lab.move(QtCore.QPoint(self._offy, 0))

    def _updatePos(self, size):
        # center in x
        x = 0.5 * size.width() - self.size().width() / 2
        pos = QtCore.QPoint(x, 0)
        self.move(pos)

    def _finish(self):
        B = QtWidgets.QMessageBox
        b = B(B.Information,
              'Closing QELA tour...',
              '''Do you want to close the tour?''',
              B.Yes | B.No)
        b.setDefaultButton(B.Yes)
        b.setWindowIcon(self.windowIcon())

        if b.exec_() == B.Yes:
            self.close()
            if self._fnClose:
                self._fnClose()

            self.gui.sigResized.disconnect(self._updatePos)

    def next(self, direction):
        self.index += direction
        
        if self.index == -1:  # begin of tour
            self.btn2.setEnabled(True)
            self.btn1.setEnabled(False)
 
        elif self.index == self._tour_len:  # end of tour
            self.btn2.setEnabled(False)
            self.btn1.setEnabled(True)
 
        else:  # somewhere in the middle
            self.btn2.setEnabled(True)
            self.btn1.setEnabled(True)

        self._nextFn(self)
        self._adjustSize()

    def _adjustSize(self):
        lb = self.lab
        lb.adjustSize()
        # limit size:
        s = lb.size()
        w0, h0 = s.width(), s.height()
        h0 += self._offy
        w, h = max(self._layHeader.minimumSize().width(), min(500, w0)), min(400, h0)
        lb.resize(w, h0)
        w += 4  #
        self.resize(w, h)
        x = w - self.btn3.size().width()
        self.btn3.move(QtCore.QPoint(x, 0))  # move close-btn to top right 


if __name__ == '__main__':
    from client.Application import Application

    app = Application()
    
    gui = QtWidgets.QWidget()
    gui.resize(600, 400)

    def fnNext(tour):
        tour.lab.setText('Fooxxxxxxxxxxxxxxxxxxx %s' % tour.index)
    
    gui.show()

    w = Tour(gui, 3, fnNext, title='TestTitle')
    w.show()
    w.next(0)
    
    app.exec_() 
