import os
import json
from textwrap import dedent
from zipfile import ZipFile

from PyQt5 import QtWidgets, QtGui, QtCore

from fancywidgets.pyQtBased.StatusBar import StatusBar

from fancytools.os.yieldOtherProgramInstances import yieldOtherProgramInstances
from fancytools.os.fileCheckSum import fileCheckSum
from fancytools.os.PathStr import PathStr
# LOCAL:
import client
from client.communication import dataArtist
from client.widgets.TabUpload import TabUpload
from client.widgets.TabDownload import TabDownload
from client.widgets.TabConfig import TabConfig
from client.widgets.TabCheck import TabCheck
from client.widgets.CancelProgressBar import CancelProgressBar
from client.widgets.Help import Help
from client.widgets.inlineView import InlineView
from client.widgets.Contact import Contact
from client.widgets.Pricing import Pricing
from client.widgets.About import About
from client.widgets.Projects import Projects
from client.widgets._Base import QMenu
from client.widgets.Account import Account
from client.widgets.Tour import Tour


class _DownloadThread(QtCore.QThread):
    sigUpdate = QtCore.pyqtSignal(int)
    sigDone = QtCore.pyqtSignal(object)

    def __init__(self, gui, dfiles, root, **kwargs):
        super().__init__()
        self.gui = gui
        self._dFiles = dfiles
        self._cancel = False
        self._root = root
        self.kwargs = kwargs
        
    def run(self):
        df = self._dFiles
        if not type(df) in (tuple, list):
            df = [df]
        ll = len(df)
        files = []

        for i, f in enumerate(df):
            if self._cancel:
                break
            if ll == 1 and self._root.isFileLike():
                # local file = root 
                localpath = self._root
            else:
                # local  file = root\relFilePath
                localpath = self._root.join(f)
            self.gui.server.download(f, localpath, **self.kwargs)
            files.append(localpath)

            self.sigUpdate.emit(int(100 * (i + 1) / ll))
        
        if ll == 1 and len(files):
            files = files[0]
        self.sigDone.emit(files)

    def kill(self):
        self._cancel = True


class MainWindow(QtWidgets.QMainWindow):
    PATH = client.PATH
    sigMoved = QtCore.pyqtSignal(QtCore.QPoint)
    sigResized = QtCore.pyqtSignal(QtCore.QSize)

    def __init__(self, login, server, user, pwd):
        super(). __init__()
        self.user = user
        self.pwd = pwd
        self.login = login
        self.server = server
        FIRST_START = not self.PATH.join(user).exists()
        self.PATH_USER = self.PATH.mkdir(user)
        # TODO: read last root from config
        self.root = self.PATH_USER.mkdir("local")
        self.updateProjectFolder()

        self._downloadQueue = []
        self._downloadThread = None
        self._tempview = None
        self._lastW = None
        self._startTourExample = False
        
        self._about, self._api, self._contact, \
            self.help, self._pricing, self._security = None, None, None, None, None, None

        self.setWindowIcon(QtGui.QIcon(client.ICON))
        self.updateWindowTitle()
        
#         QtCore.QLocale.setDefault()

        self.resize(1100, 600)

        ll = QtWidgets.QHBoxLayout()
        w = QtWidgets.QWidget()
        w.setLayout(ll)
        self.setCentralWidget(w)

        self.progressbar = CancelProgressBar()
        self.progressbar.hide()

        self.setStatusBar(StatusBar())
        self.statusBar().addPermanentWidget(self.progressbar, stretch=1)

        self.server.sigError.connect(self.statusBar().showError)

        self.btnMenu = QtWidgets.QPushButton()
        self.btnMenu.setIcon(QtGui.QIcon(
            client.MEDIA_PATH.join('btn_menu.svg')))
        # make button smaller:
        self.btnMenu.setIconSize(QtCore.QSize(20, 20))

        self.btnMenu.setFlat(True)
        self._menu = QMenu()
        
        a = self._menu.addAction('About QELA')
        a.setToolTip(About.__doc__)
        a.triggered.connect(self._menuShowAbout)
        
        a = self._menu.addAction('Help')
        f = a.font()
        f.setBold(True)
        a.setFont(f)
        a.setToolTip(Help.__doc__)
        a.triggered.connect(self._menuShowHelp)

        a = self._menu.addAction('Change current project')
        a.setToolTip(Projects.__doc__)
        a.triggered.connect(self._menuShowProjects)

        a = self._menu.addAction('Download example images')
        a.triggered.connect(self._downloadExampleImages)

        a = self._menu.addAction('Pricing')
        a.setToolTip(Pricing.__doc__)
        a.triggered.connect(self._menuShowPlan)

        a = self._menu.addAction('Website')
        a.setToolTip(
            'Open the application website in your browser')
        a.triggered.connect(self._menuShowWebsite)

        a = self._menu.addAction('Contact us')
        a.setToolTip(Contact.__doc__)
        a.triggered.connect(self.menuShowContact)

        self._menu.addSeparator()

        a = self._menu.addAction('Account')
        a.triggered.connect(self.account)

        a = self._menu.addAction('Change User')
        a.triggered.connect(self.changeUser)

        self.btnMenu.clicked.connect(self._menuPopup)
        self.btnMenu.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setCornerWidget(self.btnMenu)

        self.help = Help(self)
        self.help.hide()

        self.tabUpload = TabUpload(self)
        self.tabDownload = TabDownload(self)
        self.tabCheck = TabCheck(self)
        self.tabConfig = TabConfig(self)  # TODO: rename to tabconfig
#         self.loadConfig()

        self.tabs.addTab(self.tabConfig, "Configuration")
        self.tabs.addTab(self.tabUpload, "Upload")
        self.tabs.addTab(self.tabCheck, "Check")
        self.tabs.addTab(self.tabDownload, "Download")
        self.tabs.currentChanged.connect(self._activateTab)
        self.tabs.currentChanged.connect(self.help.tabChanged)

        self.tabs.setCurrentIndex(1)  # show TabUpload at start

        ll.setContentsMargins(0, 0, 0, 0)

        ll.addWidget(self.tabs)
        ll.addWidget(self.help)

        self._tempBars = []
        self.tabCheck.checkUpdates()
#         FIRST_START = True

        self.restoreLastSession()
        self.show()

        if FIRST_START:
            B = QtWidgets.QMessageBox
            b = B(B.Information,
                  'Starting QELA for the first time...',
                  '''Hi %s!
It looks like this is your first time using QELA on this PC.
Would you like to take a quick tour?''' % self.user,
                  B.Yes | B.No)
            b.setDefaultButton(B.Yes)
            b.setWindowIcon(self.windowIcon())

            if b.exec_() == B.Yes:
                self._tourInit()

    def saveSession(self):
        s = self.PATH_USER.join('session.json')
        c = {'config':self.tabConfig.saveState(),
             'upload':self.tabUpload.saveState(),
             'download':self.tabDownload.saveState(),
             'check':self.tabCheck.saveState(),
             }
        with open(s, 'w') as f:
            f.write(json.dumps(c, indent=4))

    def restoreConfigFromServer(self):
        self.tabConfig.restoreState(self.server.lastConfig())
 
    def restoreLastSession(self):
        try:
            s = self.PATH_USER.join('session.json')
            c = None
            if s.exists():
                try:
                    with open(s, 'r') as  f:
                        c = json.loads(f.read())
                except json.decoder.JSONDecodeError:
                    print('ERROR loading last session: %s' % c)
            if c is None:
                self.restoreConfigFromServer()
            else:
                self.tabConfig.restoreState(c['config'])
                self.tabDownload.restoreState(c['download'])
                self.tabUpload.restoreState(c['upload'])
                self.tabCheck.restoreState(c['check'])

        except Exception:
            print('Could not restore last session')

    def _downloadDoneExampleImages(self, path):
        if not hasattr(self, '_tourSa'):
            self._tourExample_init(path)
        else:
            # other tour is still running - start after that
            self._startTourExample = path
        
    def _tourExample_init(self, path):
        # TODO: temporarily disable all other tabs
        self._startTourExample = False
        dirname = path[:-4]  # remove zip
        with ZipFile(path) as myzip:
            myzip.extractall(dirname)
        QtGui.QDesktopServices.openUrl(
                QtCore.QUrl.fromLocalFile(dirname))
        
        self.tabs.setCurrentWidget(self.tabUpload)

        self._tourEx = Tour(self, 1, self._tourExNext,
                             'Correct example images',
                             self._tourExCleanUp)
        self._tourEx.show()
        self._tourEx.next(0)

    def _tourExCleanUp(self):
        if hasattr(self, '_dragWBtn_style'):
            # reset
            self.tabUpload.dragW.btn.setStyleSheet(self._dragWBtn_style)
            del self._dragWBtn_style

    def _tourExNext(self, tour):
        self._tourExCleanUp()
        if tour.index == -1:
    
            tour.lab.setText('''\
1. Select all folders in the open directory
2. Drag and drop them into QELA
3. Click on Button <Blocks>''')
        elif tour.index == 0:
            tour.lab.setText('''\
1. Click on Button <Blocks>
2. Click on Items <Measurement>, <Module ID> and <Current>
3. Move <Measurement>, <Module ID> and <Current> to position 3,4 and 5 respectively''')        
            self._dragWBtn_style = self.tabUpload.dragW.btn.styleSheet()
            self.tabUpload.dragW.btn.setStyleSheet('QPushButton { %s }' % tour.style)

        elif tour.index == 1:
            tour.lab.setText('''\
1. Ensure all field in the table are filled with meaningful data.
2. Go to tab 'Configuration' and make sure that 'exampleCalibration' is chosen as camera
3. Click un button upload to upload all images and start image processing.''')        

    def _downloadExampleImages(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(directory=self.root)
        if d:
            self.addDownload('exampleImages.zip', PathStr(d),
                             fnsDone=self._downloadDoneExampleImages,
                             cmd='exampleImages.zip')

    def _tourInit(self):
        
        B = QtWidgets.QMessageBox
        b = B(B.Information,
              'Download example images',
              '''You can start right away using our example images.
Would you like to download them now?
You can also download them at any other time (Menu->Download example images)''',
              B.Yes | B.No)
        b.setDefaultButton(B.Yes)
        b.setWindowIcon(self.windowIcon())
        if b.exec_() == B.Yes:
            self._downloadExampleImages()
            
        self._tourSa = Tour(self, 4, self._tourNext,
                             'First Steps',
                             self._tourClose)
#         self._tourSa.show()
#         self._tourSa.next(0)

        QtCore.QTimer.singleShot(0, lambda: [self._tourSa.show(),
                                             self._tourSa.next(0)])
#                                              self._tourSa.adjustSize)

    def _tourClose(self):
        self.tabs.setStyleSheet('')
        self.btnMenu.setStyleSheet('')
        del self._tourSa

        if self._startTourExample:
            self._tourExample_init(self._startTourExample)

#             self.tabUpload.dragW.btn.setStyleSheet('')

    def _tourNext(self, tour):
        
#         self._tour_btn1.setEnabled(self._tour_index >-2)

        if tour.index == -1:  # begin of tour
            doc = About.FIRST_STEPS
            self.tabs.setStyleSheet('')

        elif tour.index == 4:  # end of tour

            self._menuPopup()
            doc = '''Click on HELP(-->) to show this help again and to 
highlight all all input fields with a tooltip'''
            self.tabs.setStyleSheet('')
            self.btnMenu.setStyleSheet('QPushButton { %s }' % tour.style)

        else:  # somewhere in the middle

            self.tabs.setCurrentIndex(tour.index)
            w = self.tabs.currentWidget()
            doc = w.__doc__
            self.btnMenu.setStyleSheet('')
            self.tabs.setStyleSheet('QTabBar::tab:selected { %s }' % tour.style)
            
#             if self.tabs.currentWidget() == self.tabUpload:
#                 # highlight block button:
#                 self._dragWBtn_style = self.tabUpload.dragW.btn.styleSheet()
#                 self.tabUpload.dragW.btn.setStyleSheet('QPushButton { %s }' % style)
#             elif hasattr(self, '_dragWBtn_style'):
#                 # reset
#                 self.tabUpload.dragW.btn.setStyleSheet(self._dragWBtn_style)
#                 del self._dragWBtn_style

        doc = dedent(doc).rstrip().lstrip()
        tour.lab.setText(doc.replace('\n', '<br>'))  # '<br><br>' + 
#         self._initTourWidgetResize()

    def updateProjectFolder(self):
        self._proj = self.server.projectCode()
        self.root.mkdir(self._proj)

    def projectFolder(self):
        return self.root.join(self._proj)

    def _menuShowProjects(self):
        self._projects = Projects(self)
        self._projects.show()

#     def loadConfig(self):
#         try:
#             c = self.server.lastConfig()
#             self.config.restore(c)
#         except json.decoder.JSONDecodeError:
#             print('ERROR loading last config: %s' % c)

    def updateWindowTitle(self, project=None):
        if project is None:
            project = self.server.projectName()
        self.setWindowTitle('QELA | User: %s | Project: %s | Credit: %s' % (
            self.user, project, self.server.remainingCredit()))

    def _menuShowAbout(self):
        if self._about is None:
            self._about = About(self)
        self._about.show()

    def _menuShowHelp(self):
        if self.help.isVisible():
            self.help.hide()
        else:
            self.help.show()

    def _menuShowWebsite(self):
        os.startfile('https://%s' % self.server.address[0])

    def _menuShowPlan(self):
        if self._pricing is None:
            self._pricing = Pricing(self)
        self._pricing.show()

    def menuShowContact(self):
        if self._contact is None:
            self._contact = Contact(self)
        self._contact.show()

    def modules(self):
        '''return a list of all modules either found in imageuploadtable (from client)
        or tabCheck (from server)'''
        ll = list(self.tabCheck.modules())
        ll.extend(self.tabUpload.table.modules())
        return set(ll)

    def verifyFile(self, path, warning=True):
        '''
        returns True if local file could be verified
        '''
        localpath = self.projectFolder().join(path)
        checksum = fileCheckSum(localpath)
        verified = self.server.verifyFile(path, checksum)
        if not warning:
            return verified
        if not verified:
            ret = QtWidgets.QMessageBox.warning(self, 'Verification error', '''File <{}> 
could  not be verified by our server. 
It is possible, that is has been tampered with. 
Would you like to  download it again?.

'''.format(path), QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            return ret == QtWidgets.QMessageBox.Yes
        return True

    def openImage(self, path, **kwargs):
        txt = self.tabConfig.preferences.cbViewer.currentText()
        if txt == 'dataArtist':
            dataArtist.importFile(path)
        elif txt == 'Inline':
            if self._tempview is None:
                self._tempview = InlineView()
            self._tempview(path, **kwargs)
        else:
            os.startfile(path)

    def _menuPopup(self):
        g = self.btnMenu.geometry()
        p = g.bottomLeft()
        p.setX(p.x() - (self._menu.sizeHint().width() - g.width()))
        self._menu.popup(self.mapToGlobal(p))

    def removeTemporaryProcessBar(self, bar):
        self._tempBars.remove(bar)
        self.statusBar().removeWidget(bar)
#         self.progressbar.show()

    def addTemporaryProcessBar(self):
        c = CancelProgressBar()
        self._tempBars.append(c)
        self.progressbar.hide()
        self.statusBar().addPermanentWidget(c, stretch=1)
        return c

    def moveEvent(self, evt):
        self.sigMoved.emit(evt.pos())
        
    def resizeEvent(self, evt):
        self.sigResized.emit(evt.size())

    def closeEvent(self, ev):
        if not self.server.isReady():
            msg = QtWidgets.QMessageBox()
            msg.setText("You are still uploading/downloading data")
            msg.setStandardButtons(
                QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
            msg.exec_()
            if msg.result() == QtWidgets.QMessageBox.Ok:
                ev.accept()
            else:
                ev.ignore()
                return
        self._close()

    def _downloadDone(self):
        self._downloadThread = None
        self.progressbar.hide()

        if len(self._downloadQueue):
            # work on next in queue
            self.addDownload(*self._downloadQueue.pop(0))

    def addDownload(self, paths, root, fnsDone=None, **kwargs):
        '''
        paths tuple/list -> multiple files, str/Pathstr -> single file
        fnsDone tuple/list -> multiple functions, else -> single function
        
        roon ... either local to-file or download folder
        '''
        b = self.progressbar
        if self._downloadThread is None:
            d = self._downloadThread = _DownloadThread(self, paths, root, **kwargs)
            if fnsDone is not None:
                if type(fnsDone) not in  (tuple, list):
                    fnsDone = [fnsDone]
                for fn in fnsDone:
                    d.sigDone.connect(fn)
            d.sigUpdate.connect(b.bar.setValue)
            d.sigDone.connect(self._downloadDone)
            d.start()

            b.setColor('darkblue')
            b.bar.setFormat("Downloading %p%")
            b.setCancel(d.kill)
            b.show()
        else:
            # already downloading something: add this one to queue
            self._downloadQueue.append((paths, root, fnsDone))

    def _close(self):
        self.saveSession()
        if self.server.isReady():
            self.hide()  # yieldOtherProgramInstances is quite slow, so close win first
            if not len(list(yieldOtherProgramInstances())):
                # is this window is the only one - no other client is opened:
                self.server.logout()

    def account(self):
        a = getattr(self, '_account', None) 
        if not a:
            self._account = a = Account(self)
        a.show()

    def changeUser(self):
        self.close()
        L = self.login.__class__(self.server, True)
        L.show()

    def setTabsEnabled(self, enable=True, exclude=None):
        for i in range(self.tabs.count() - 1):
            if i != exclude:
                self.tabs.setTabEnabled(i, enable)
        if enable:
            self.tabs.setCurrentIndex(2)

    def _activateTab(self, index):
        w = self.tabs.widget(index)
        if self._lastW and hasattr(self._lastW, 'deactivate'):
            self._lastW.deactivate()
        if hasattr(w, 'activate'):
            w.activate()
        self._lastW = w
