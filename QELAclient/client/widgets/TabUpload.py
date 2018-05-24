from PyQt5 import QtWidgets, QtCore, QtGui

from fancytools.os.PathStr import PathStr
# LOCAL
from client.widgets._table import ImageTable, DragWidget
from client.widgets._Base import QMessageBox

IMG_FILETYPES = ('tiff', 'tif', 'jpg', 'jpeg',
                 'bmp', 'jp2', 'png')


class _UploadThread(QtCore.QThread):
    sigUpdate = QtCore.pyqtSignal(bool)
    sigDone = QtCore.pyqtSignal(int)

    def __init__(self, paths, table, server):
        super().__init__()
        self.paths = paths
        self.table = table
        self.server = server

    def run(self):
        for index, p in enumerate(self.paths):
            self.server.upload(p, self.sigUpdate)
            self.sigDone.emit(index)


class _ServerAgendas(QtWidgets.QWidget):

    def __init__(self, tab):
        QtWidgets.QWidget.__init__(self)
        self.tab = tab
        self._name = None
        ll = QtWidgets.QHBoxLayout()
        self.setLayout(ll)

        self.comboAgenda = QtWidgets.QComboBox()
#         self.comboAgenda.activated.connect(self._buildAgendaMenu)
        self.comboAgenda.currentTextChanged.connect(self.tab._chooseAgenda)

        self._buildAgendaMenu()

        self.comboAgenda.currentTextChanged.connect(self.agendaChanged)

        self.ckUploaded = QtWidgets.QCheckBox('Uploaded')
        self.ckUploaded.setEnabled(False)
        
        self.ckProcessed = QtWidgets.QCheckBox('Processed')
        self.ckProcessed.setEnabled(False)
        
        self.btnReuse = QtWidgets.QPushButton('Use for new agenda')
        self.btnReuse.setToolTip('Click, to create a new job from this agenda.')
        self.btnReuse.clicked.connect(self._reuse)

        self.btnRemove = QtWidgets.QPushButton('Remove from server')
        self.btnRemove.setToolTip('Remove current agenda and all its files from the server')
        self.btnRemove.clicked.connect(self._remove)

        ll.addWidget(QtWidgets.QLabel("Agenda: "))
        ll.addWidget(self.comboAgenda)

        ll.addWidget(self.ckUploaded)
        ll.addWidget(self.ckProcessed)
        ll.addWidget(self.btnReuse)
        ll.addWidget(self.btnRemove)
        
        self._hide()

    def text(self):
        return self.comboAgenda.currentText()

    def toCurrent(self):
        self.comboAgenda.setCurrentText('CURRENT')

    def setDone(self, name):
        # if current agenda == name:
        #     check 'processed' 
        if self.text() in ('CURRENT', name):
            self.ckProcessed.setChecked(True)

    def isCurrent(self):
        return self.text() == 'CURRENT'

    def _hide(self):
        self.ckProcessed.hide()
        self.ckUploaded.hide()
        self.btnReuse.hide()
        self.btnRemove.hide()

    def _show(self):
        self.ckProcessed.show()
        self.ckUploaded.show()
        self.btnReuse.show()
        self.btnRemove.show()

    def _buildAgendaMenu(self):
        tt = self.comboAgenda.currentText()
        self.comboAgenda.clear()
        items = ['CURRENT']
        items.extend([f.basename()[:-4] for f in
                      self.tab.gui.PATH_USER.join('upload').files()][::-1])
        self.comboAgenda.blockSignals(True)
        self.comboAgenda.addItems(items)
        if tt in items:
            self.comboAgenda.setCurrentText(tt)
        self.comboAgenda.blockSignals(False)

    def _remove(self):
        # TODO: server will only look in current project folder ... 
        # maybe only show local agendas of the current project
        
        # remove the current agenda from the server
        if QtWidgets.QMessageBox.warning(self, "Removing current agenda",
                    'Are you sure?') != QtWidgets.QMessageBox.Ok:
            return
        res = self.tab.gui.server.removeAgenda(self.text())
        if res != 'OK':
            QtWidgets.QMessageBox.critical(self, "Error removing current agenda",
                    res, QtWidgets.QMessageBox.Ok)
        else:
            self._reuse()

    def  _reuse(self):
        self.comboAgenda.blockSignals(True)
        self.comboAgenda.setCurrentText('CURRENT')
        self.comboAgenda.blockSignals(False)
        self._setState(True, False, False)

    def agendaChanged(self, name):
        self._name = name
        if name == 'CURRENT':
            self._setState(True, False, False)
        else:
            a = self.tab.gui.server.stateAgenda(name).split(', ')  # TODO: parse server output
            exists, processed = a[0] == 'True', a[1] == 'True'
            self._setState(False, exists, processed)
    
    def _setState(self, current, exists, processed):
        self.ckUploaded.setChecked(exists)
        self.ckProcessed.setChecked(processed)
        if exists:
            txt = 'Process'
        else:
            txt = 'Upload'
        self.tab.btnUpload.setText(txt)
        if current:
            self._hide()
        else:
            self._show()            
        self.tab.table.setEnabled(current)
        self.tab.cbMetaData.setEnabled(current)


class TabUpload(QtWidgets.QWidget):
    '''
    To import  your measurements, drag/Drop one or multiple directories/files.
    Accepted image types are: %s.

    We advise to capture EL at <b>2 or more currents</b>.
    * for 2 Currents: 20%% I_sc, 100%% I_sc
    * for 3 currents: 20%% I_sc, 50%% I_sc, 100%% I_sc
    
    Especially in the existence of environmental light or variable light conditions
    a <b>background image</b> should be captured with the came camera setup.
    
    If exposure times of longer than 2 minutes and/or the EL signal is low, 
    certain image artifacts (single time effects) can be found disturbing.
    
    If 2 or more (EL and BG) images are provided those artifacts can be filtered 
    AND the signal stability can be better estimated.   

    Before uploading the images (top right button), please ensure that you provide
    measurement current, module ID, date and if possible measurement name and camera parameters.
    
    Instead of entering all field by hand, you can also read all information from the file path.
    For this, either use predefined or own BLOCKS. 
    
    Please note, that image correction can be conducted,  even if no further information is available.
    
    <ul>To allow certain image processing routines you need to provide the following information: \
        <li> image intensity correction -> exposure time,  ISO and f-number </li> \
        <li> Module identification in PDF report and download tab -> Measurement number, name and current </li> \
        <li> Power/Energy loss mapping -> Measurement current </li> \
        <li> Enable complete camera calibration -> fnumber and ISO </li> \
    </ul>
    '''

    def __init__(self, gui):
        super().__init__()
        self.__doc__ = self.__doc__ % str(IMG_FILETYPES)

        ll = QtWidgets.QVBoxLayout()
        self.setLayout(ll)

        self.gui = gui
        self._tableTempState = ()
        self.setAcceptDrops(True)
        lheader = QtWidgets.QHBoxLayout()

        self.cbMetaData = btn1 = QtWidgets.QCheckBox('Read image meta data')
        self.cbMetaData.setChecked(True)
        self.cbMetaData.setToolTip(
            'Read camera parameters from file meta data / this will slow the import down')
        self.cbMetaData.clicked.connect(self._btnAddMetaDataClicked)

        self.serverAgendas = _ServerAgendas(self)

        self.btnUpload = btn3 = QtWidgets.QPushButton('Upload')
        self.btnUpload.setEnabled(False)
        
        btn3.clicked.connect(self.upload)

        lheader.addWidget(btn1, alignment=QtCore.Qt.AlignLeft, stretch=0)
        lheader.addSpacing(50)

        lheader.addWidget(self.serverAgendas,
                          alignment=QtCore.Qt.AlignLeft, stretch=0)
        lheader.addStretch()

        self.labelState = QtWidgets.QLabel()
        lheader.addWidget(
            self.labelState, alignment=QtCore.Qt.AlignRight, stretch=0)

        lheader.addWidget(btn3, alignment=QtCore.Qt.AlignRight, stretch=0)
        ll.addLayout(lheader)

        self._layPath = QtWidgets.QGridLayout()
        ll.addLayout(self._layPath)

        self.lab = QtWidgets.QLabel("""<h1>Drag'N'Drop</h1>one or more Files of Folders<br>Supported image types:<br>%s
<br>Drop a CSV-file to directly import an agenda.""" % str(IMG_FILETYPES)[1:-1])
        ll.addWidget(self.lab, alignment=QtCore.Qt.AlignCenter, stretch=1)
        self.dragW = d = DragWidget()
        self._layPath.addWidget(d)

        self.table = ImageTable(self)
        self.table.filled.connect(self._tableFilled)
        self.table.sigIsEmpty.connect(self._initState)

        ll.addWidget(self.table, stretch=1)

    def saveState(self):
        return {'blocks':self.dragW.saveState(),
                'meta':self.cbMetaData.isChecked(),
                'table':self.table.saveState()}
        
    def restoreState(self, state):
        self.cbMetaData.setChecked(state['meta'])
        self.dragW.restoreState(state['blocks'])
        if len(state['table']):
            self.setViewFilled()
            self.table.fillFromState(state['table'])
        
    def _btnAddMetaDataClicked(self, checked):
        th = self.table.threadAddMetadata 
        if checked:
            if th is None or not th.isRunning():
                self.btnUpload.setEnabled(False)
                self.table.addMetaData()
        else:
            # stopp adding meta date since checkbox 'add metadata' was unchecked
            if th is not None and th.isRunning():
                th.kill()

    def _tableFilled(self):
        self._enableUpbloadBtn()
        self.setAcceptDrops(True)

    def _initState(self):
        self.btnUpload.setEnabled(False)
#         self.dragW.hide()
#         self.table.hide()
#         self.serverAgendas.hide()
#         self.lab.show()
        self.setViewFilled(False)
        self.setAcceptDrops(True)

    def _chooseAgenda(self, txt):
        if txt:
            self.dragW.show()
            self.table.show()
            self.serverAgendas.show()
            self.lab.hide()

            if txt != 'CURRENT':
                # save current
                self._tableTempState = self.table.saveState()
                # load from file:
                path = self.gui.PATH_USER.join('upload', txt + '.csv')
                self.table.fillFromFile(path)
            else:
                if len(self._tableTempState):
                    self.table.fillFromState(self._tableTempState)
                else:
                    self._initState()

    def _checkUploadPossible(self):
        if self.table.checkValid() and self.gui.tabConfig.checkValid(): 
            return True
        return False

    def _updateContingentMsg(self):
        if self.gui.server.isReady():
            iused, contingent, memused, memavail = self.gui.server.userPlan()
            self.labelState.setText(
                'Measurements: %s / %s daily    Memory: %s / %s GB' % (
                    iused, contingent, memused, memavail))

    def activate(self):
        self._updateContingentMsg()

    def upload(self):
        if not self._checkUploadPossible():
            # information provided is incomplete
            return

        # limit number of locally stored upload agendas:
        MAX_AGENDAS = 800
        fol = self.gui.PATH_USER.mkdir('upload')
        files = fol.listdir()
        if len(files) > MAX_AGENDAS:
            for f in files[-MAX_AGENDAS:]:
                fol.join(f).remove()

        # CONFIG:
        CC = QtWidgets.QMessageBox.critical
            # upload
        status, msg = self.gui.server.setConfig(self.gui.tabConfig.toStr())
        if status == 'Error':
            return CC(self, "Could not upload config",
                      msg, QtWidgets.QMessageBox.Ok)
        elif status == 'Warning':
            box = QMessageBox.build(self, buttons=QtWidgets.QMessageBox.Ok | 
                              QtWidgets.QMessageBox.Cancel,
                              title="Config file was modified by the server",
                              icon=QtWidgets.QMessageBox.Warning,
                              text=msg)
            if box.exec_() == QtWidgets.QMessageBox.Cancel:
                return    
            
        if not self.serverAgendas.isCurrent():
            # process images using agenda which is already on the server
            agenda = self.serverAgendas.text()
            status, agenada_name = self.gui.server.setAgenda(agenda)
            self._currentJob = agenada_name
            if status != 'OK':
                return CC(self, "Could not re-use agenda ",
                                agenada_name, QtWidgets.QMessageBox.Ok)
            return self._progressImgs()

        # upload new agenda and images
        # AGENDA:
            # upload server version
        csvstr, new_paths = self.table.toCSVStr(local=False)        
        status, agenada_name = self.gui.server.setAgenda(csvstr)
        self._currentJob = agenada_name

        if status != 'OK':
            plocal = fol.join('FAIL') + '.csv'
            with open(plocal, 'w') as f:
                f.write(csvstr)
            return CC(self, "Could not upload agenda ",
                            agenada_name , QtWidgets.QMessageBox.Ok)

            # save local
        csvstr, paths = self.table.toCSVStr()
        plocal = fol.join(agenada_name) + '.csv'
        with open(plocal, 'w') as f:
            f.write(csvstr)

        price = self.gui.server.priceCurrentJob()
        if price.split(' ')[0] != '0':
            box = QMessageBox.build(self, buttons=QtWidgets.QMessageBox.Ok | 
                              QtWidgets.QMessageBox.Cancel,
                              title="PRO features are used",
                              icon=QtWidgets.QMessageBox.Information,
                              text='''If you proceed,\nyour account will be credited:\n%s''' % price)
            if box.exec_() == QtWidgets.QMessageBox.Cancel:
                return    

        self.table.uploadStart()
        self.setAcceptDrops(False)
        self.dragW.setEnabled(False)
        self.btnUpload.setEnabled(False)
        
        h = QtWidgets.QTableWidgetItem()
        h.setText('Progress')
        b = self.gui.progressbar
        b.setColor('darkred')
        b.setCancel(self.cancelUpload)
        b.show()
        self.gui.server.upload(paths, new_paths,
            self.table.uploadUpdate, self._uploadDone, self._uploadError)

    def _uploadError(self, msg):
        QtWidgets.QMessageBox.critical(self, "Error uploading file",
                    msg, QtWidgets.QMessageBox.Ok)
        self.cancelUpload()

    def _uploadDone(self):
        self.serverAgendas._buildAgendaMenu()

        self.gui.progressbar.hide()
        self.setAcceptDrops(True)
        self.dragW.setEnabled(True)
        
#         self.lab.show()
#         self.serverAgendas.hide()
#         self.dragW.hide()
#         
        self.setViewFilled(False)

        self.table.uploadDone(self.serverAgendas.isCurrent())
        
        self._progressImgs()

    def _progressImgs(self):
        res = self.gui.server.processImages()
        if res != 'OK':
            QtWidgets.QMessageBox.critical(self, "Error processing images",
                    res, QtWidgets.QMessageBox.Ok)
            self._enableUpbloadBtn()
            return
            
        self.btnUpload.setEnabled(False)
        
        self._timer = QtCore.QTimer()
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._updateProgressImages)
        self._timer.start()
        
        b = self.gui.progressbar
        b.setColor('purple')
        b.setCancel(self._processingCanceled)
        b.show()
        
        self._updateProgressImages()
        self._updateContingentMsg()
        self.gui.updateWindowTitle()

    def _processingCanceled(self):
        self.gui.server.stopProcessing()
        self._enableUpbloadBtn()
        
    def _enableUpbloadBtn(self):
        if self.table.isVisibleTo(self) and not self.gui.progressbar.isVisible():
            self.btnUpload.setEnabled(True)

    def _updateProgressImages(self):
        if self.gui.server.isReady():
            s = self.gui.server.stateProcessing()
            b = self.gui.progressbar
            try:
                # extract value from e.g. 'Correct Images 13%'
                i = s[::-1].index(' ')
                val = int(s[-i:-1])
                txt = s[:-i] + '%p%'
                b.bar.setValue(val)
                b.bar.setFormat(txt)
#                 if val == 100:

            except ValueError:
                
                def finish():
                    self._timer.stop()
                    b.hide()
                    del self._timer
                    self._enableUpbloadBtn()
                    
                if s == 'DONE':
                    finish()
                    self.serverAgendas.setDone(self._currentJob)
                elif s.startswith('ERROR'):
                    finish()
                    self.gui.statusBar().showError(s)
                else:
                    b.bar.setValue(0)
                    b.bar.setFormat(s)

    def cancelUpload(self):
#         self.gui.progressbar.hide()
        self.gui.server.cancelUpload()
        self.table.uploadCancel()

        self.setAcceptDrops(True)
        self.dragW.setEnabled(True)

    def keyPressEvent(self, event):
        if event.matches(QtGui.QKeySequence.Paste):
            self.dropEvent(QtWidgets.QApplication.clipboard())

    def dragEnterEvent(self, event):
        m = event.mimeData()
        if (m.hasUrls()):
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def _getFilePathsFromUrls(self, urls):
        '''
        return a list of all file paths in event.mimeData.urls()
        '''
        limg, lagenda = [], []

        def _appendRecursive(path):
            if path.isfile():
                if path.filetype() in IMG_FILETYPES:
                    limg.append(path)
                elif path.filetype() == 'csv':
                    lagenda.append(path)
            else:
                for f in path:
                    # for all files in folder
                    _appendRecursive(path.join(f))

        # one or more files/folders are dropped
        for url in urls:
            if url.isLocalFile():
                path = PathStr(url.toLocalFile())
                if path.exists():
                    _appendRecursive(path)
        return limg, lagenda

    def setViewFilled(self, filled=True):
        self.lab.setVisible(not filled)
        self.table.setVisible(filled)
        self.dragW.setVisible(filled)  
        if not filled:      
            self.serverAgendas.toCurrent()

    def dropLines(self, lines):
        self.setViewFilled()
        self.table.fillFromState(lines, appendRows=True)

    def dropEvent(self, event):
        m = event.mimeData()
        if m.hasUrls():
            self.btnUpload.setEnabled(False)

            pathimgs, pathagendas = self._getFilePathsFromUrls(m.urls())
            if pathimgs or pathagendas:
                self.setViewFilled()
            if pathimgs:
                self.setAcceptDrops(False)
#                 self.dragW.setExamplePath(pathimgs[0])
                self.table.fillFromPaths(pathimgs)
            for p in pathagendas:
                self.table.fillFromFile(p, appendRows=True)
            if not pathimgs and pathagendas:
                self.setAcceptDrops(True)
