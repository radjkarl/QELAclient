from PyQt5 import QtWidgets, QtGui
from textwrap import dedent

# class QLabel(QtWidgets.QLabel):
#     '''
#     a blue underlined label with .clicked signal
#     '''
#     clicked = QtCore.pyqtSignal()
#
#     def __init__(self, txt):
#         QtWidgets.QLabel.__init__(self, txt)
#         self.setStyleSheet(
#             "QLabel { color: blue; text-decoration: underline;}")
#
#     def mousePressEvent(self, evt):
#         if evt.button() != QtCore.Qt.LeftButton:
#             return
#         self.clicked.emit()


class Help(QtWidgets.QWidget):

    def __init__(self, gui):
        QtWidgets.QWidget.__init__(self)
        self.gui = gui

        self._contact = None
        self._api = None
        self._about = None

        self.setFixedWidth(300)
#         self._lastFrame = None
        pal = self.palette()
        pal.setColor(QtGui.QPalette.Background, QtGui.QColor('#e2e4ed'))
        self.setAutoFillBackground(True)
        self.setPalette(pal)

        ll = QtWidgets.QVBoxLayout()
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        self.setLayout(ll)
        self.ltop = QtWidgets.QHBoxLayout()
        self.ltop.setSpacing(11)

        self.lab_tab = QtWidgets.QLabel('Tab')
        self.ltop.addWidget(self.lab_tab)

        btnClose = QtWidgets.QPushButton(self)
        btnClose.setFlat(True)
        btnClose.clicked.connect(self.hide)
        btnClose.setIcon(QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.SP_DialogCloseButton))  # SP_TitleBarCloseButton
        btnClose.resize(15, 15)
        self.ltop.addStretch()
        self.ltop.addWidget(btnClose, stretch=0)

        self.browser = QtWidgets.QTextBrowser()
        self.browser2 = QtWidgets.QTextBrowser()

        ll.addLayout(self.ltop, 0)
        ll.addWidget(self.browser, 0)
        self.lab_selected = QtWidgets.QLabel('Selected:  none')
        ll.addWidget(self.lab_selected, 0)
        ll.addWidget(self.browser2, 100)
#         ll.addStretch()

        self.browser2.hide()
        self.lab_selected.hide()

    def _decorateCurrentTab(self):
        tab = self.gui.tabs.currentWidget()

        if not tab:
            return

        if self.isVisible():
            style = '''background-color: rgb(102, 153, 255, 100);'''
            brush = QtGui.QBrush(QtGui.QColor(102, 153, 255, 100))
            self._old = None
        else:
            style = ''
            brush = QtWidgets.QTableWidgetItem().background()
            
        for ch in tab.findChildren(QtWidgets.QWidget):
            # all child widgets:
            h = self._widgetHelp(ch)
            if h:
                if hasattr(ch, 'setStyleSheet'):
                    ch.setStyleSheet(style)
                    
                    sig = getattr(ch, 'clicked', getattr(ch, 'activated', None))
                    if sig:        
                        if style:
                            ch._mousePressEvent = ch.mousePressEvent
                            ch.mousePressEvent = lambda evt, ch = ch: self._chClicked(evt, ch)
                        elif hasattr(ch, '_mousePressEvent'):
                            ch.mousePressEvent = ch._mousePressEvent
                            del ch._mousePressEvent
                        
                # all horizontal table header items:
                elif isinstance(ch, QtWidgets.QTableWidget):
                    for c in range(ch.columnCount()):
                        # FIXME: setBackground currently has no effect, see
                        # https://bugreports.qt.io/browse/QTBUG-57637
                        item = ch.horizontalHeaderItem(c)
                        item.setBackground(brush)
                        ch.setHorizontalHeaderItem(c, item)

    def tabChanged(self, index):
        w = self.gui.tabs.widget(index)
        if w.__doc__:
            self.browser.setHtml(dedent(w.__doc__).lstrip().replace('\n', '<br>'))
        else:
            self.browser.setText('')
        self.lab_tab.setText('Tab:  %s' % self.gui.tabs.tabText(index))
        self._decorateCurrentTab()

    def _widgetHelp(self, w):
        tt = w.toolTip()
        if tt:
            return tt
        try:
            if hasattr(w, 'help'):
                return w.help
        except NameError:
            return ''

    def _update(self, old, new):
        # set widget style of currently and previous widget
        if old is not None:
            if hasattr(old, 'lastStyle'):
                old.setStyleSheet(old.lastStyle)
#             else:
#                 old.setStyleSheet('')
        if new is not None:
            hel = self._widgetHelp(new)
            if hel:
                new.lastStyle = new.styleSheet()
                new.setStyleSheet('''background-color: rgb(97, 97, 97); 
 border-style: outset;
 border-width: 1px;
 border-color: rgb(0, 0, 0);
 border-radius: 4px;
 color:rgb(255, 255, 255);''')
            self.browser2.setText(hel)

            if hasattr(new, 'text'):
                name = new.text()
            elif hasattr(new, 'title'):
                name = new.title()
            else:
                name = 'none'
            if name == 'none':
                self.browser2.hide()
                self.lab_selected.hide()
            else:
                self.lab_selected.setText('Selected option:  %s' % name)
                self.browser2.show()
                self.lab_selected.show()

        else:
            self.browser2.hide()
            self.lab_selected.hide()

    def _chClicked(self, evt, ch):
        if ch != self._old:
            self._update(self._old, ch)
            self._old = ch   
        ch._mousePressEvent(evt) 

    def show(self):
        super().show()
        if self.gui is not None:
            self._decorateCurrentTab()

    def hide(self):
        super().hide()
        self._decorateCurrentTab()


if __name__ == '__main__':
    import sys
    #######################
    # temporary fix: app crack doesnt through exception
    # https://stackoverflow.com/questions/38020020/pyqt5-app-exits-on-error-where-pyqt4-app-would-not
    sys.excepthook = lambda t, v, b: sys.__excepthook__(t, v, b)
    #######################
    app = QtWidgets.QApplication([])
    w = Help(None)

    w.show()
    app.exec_()
