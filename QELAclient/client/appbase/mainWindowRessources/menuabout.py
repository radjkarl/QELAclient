from PyQt5 import QtWidgets, QtSvg, QtGui, QtCore


class MenuAbout(QtWidgets.QWidget):
    """Create a simple 'about' window, showing a logo
    and general information defined in the main modules __init__.py file
    """

    def __init__(self, parent=None):
        super(MenuAbout, self).__init__(parent)
        self.setWindowTitle('About')
        lv = QtWidgets.QVBoxLayout()
        lh = QtWidgets.QHBoxLayout()
        lv.addLayout(lh)
        self.setLayout(lv)

        self.label_txt = QtWidgets.QLabel()
        lh.addWidget(self.label_txt)
        self.tabs = None

    def setLogo(self, path):
        logo = QtSvg.QSvgWidget(path)
        s = logo.sizeHint()
        aR = s.height() / s.width()
        h = 150
        w = h / aR
        logo.setFixedSize(w, h)

        self.layout().itemAt(0).insertWidget(0, logo)

    def setModule(self, mod):
        """
        fill the about about label txt with the module attributes of the module
        """
        self.setInfo(getattr(mod, 'name', mod.__name__),
                     mod.__doc__, mod.__author__, mod.__email__,
                     mod.__version__, mod.__license__, mod.__url__)

    def setInfo(self, name, info, author, email, version, license_, url):
        self.setWindowTitle('About %s' % name)

        txt = """<b>%s</b> - %s<br><br>
Author:        %s<br>
Email:        %s<br>
Version:        %s<br>
License:        %s<br>
Url:            <a href="%s">%s</a>""" % (
            name, info, author, email,
            version, license_, url, url)
        self.label_txt.setText(txt)
        self.label_txt.setOpenExternalLinks(True)

    def setInstitutionLogo(self, pathList):
        """
        takes one or more [logo].svg paths
            if logo should be clickable, set
                pathList = (
                (my_path1.svg,www.something1.html),
                (my_path2.svg,www.something2.html),
                ...)
        """
        for p in pathList:
            url = None
            if type(p) in (list, tuple):
                p, url = p
            logo = QtSvg.QSvgWidget(p)
            s = logo.sizeHint()
            aR = s.height() / s.width()
            h = 150
            w = h / aR
            logo.setFixedSize(int(w), int(h))
            self.layout().itemAt(0).addWidget(logo)
            if url:
                logo.mousePressEvent = lambda evt, u = url: self._openUrl(evt, u)
                logo.setCursor (QtCore.Qt.PointingHandCursor)
#                 logo.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse)

    @staticmethod
    def _setAsLink(widget):
        widget.setOpenExternalLinks(True)
        widget.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse)

    def addTab(self, title, widgetOrText):
        if self.tabs is None:
            self.tabs = QtWidgets.QTabWidget()
            self.layout().addWidget(self.tabs)
        if isinstance(widgetOrText, QtWidgets.QWidget):
            widget = widgetOrText
        else:
            widget = QtWidgets.QTextBrowser()
            widget.setReadOnly(True)
            widget.setHtml(widgetOrText)
            widget.setOpenExternalLinks(True)

        self.tabs.addTab(widget, title)

    def _openUrl(self, evt, url):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))
        return evt.accept()


if __name__ == '__main__':
    import sys
    from fancytools.os.PathStr import PathStr
    #######################
    # temporary fix: app crack doesnt through exception
    # https://stackoverflow.com/questions/38020020/pyqt5-app-exits-on-error-where-pyqt4-app-would-not
    sys.excepthook = lambda t, v, b: sys.__excepthook__(t, v, b)
    #######################
    app = QtWidgets.QApplication([])

    p = PathStr(__file__).dirname().dirname().join(
        'media', 'icons', 'approve.svg')

    w = MenuAbout()
    w.setLogo(p)
    w.setInstitutionLogo((p,))
    w.setInfo('name', 'info', 'author', 'email', 'version', 'license_', 'url')
    w.addTab('About', 'This is a text')

    w.show()
    app.exec_()
