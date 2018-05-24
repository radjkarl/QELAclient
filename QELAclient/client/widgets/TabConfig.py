import os
import base64
import json

from PyQt5 import QtWidgets, QtGui, QtCore

from fancytools.os.PathStr import PathStr
# LOCAL
from client.widgets.ButtonGroupBox import ButtonGroupBox
from client.dialogs import FilenameInputDialog
from client._html import imageToHTML
from client._html import toHtml
from client.widgets.Projects import PNameValidator
from client.widgets._Base import QMenu
from client.widgets.base.Table import Table

IMG_HELP = PathStr(__file__).dirname().dirname().join('media', 'help')


class TabConfig(QtWidgets.QScrollArea):
    '''
    This tab includes all preferences of the images you are about to upload.
    You can choose how images should be corrected, what information should be
    collected and whether you want to receive a PDF report.
    Rest the mouse on a parameter or click on Menu->Help to receive further information.
    '''

    def __init__(self, gui):
        super(). __init__()
        self.gui = gui
        self.setWidgetResizable(True)

        self.inner = QtWidgets.QFrame(self)
        linner = QtWidgets.QHBoxLayout()
        self.inner.setLayout(linner)

        self.setWidget(self.inner)

        self.preferences = a = _Preferences(gui)
        self.location = _Location(self)
        self.modules = _ModTable(self, gui)

        self._addWidget(self.preferences, 'General', self.preferences)
        self._modulesGroup = self._addWidget(self.modules, 'Modules',
                                                horiz_stretch=True,
                                                vert_stretch=True)
        self._addWidget(self.location, 'Location', self.location)

        a.cbEnergyLoss.toggled.connect(self.cbEnergyLoss_clicked)
        a.cbEnergyLoss.toggled.connect(self._checkSetModulesTableEnabled)
        a.cbPerf.toggled.connect(self._checkSetModulesTableEnabled)
        a.cbQual.toggled.connect(self._checkSetModulesTableEnabled)
        a.cbQual.toggled.connect(lambda checked:
                                 self.modules.setColumnHidden(1, not checked))
        a.cbPerf.toggled.connect(lambda checked:
                                 [self.modules.setColumnHidden(i, not checked) for i in (2, 3)])
        [self.modules.setColumnHidden(i, True) for i in range(2, 6)]

        self.cbEnergyLoss_clicked(a.cbEnergyLoss.isEnabled())
        self._checkSetModulesTableEnabled()

    def checkValid(self):
        '''returns whether configuration is complete'''
        return self.modules.checkValid()

    def _checkSetModulesTableEnabled(self):
        a = self.preferences
        v = (a.cbEnergyLoss.isChecked() or
             a.cbPerf.isChecked() or
             a.cbQual.isChecked())
        self._modulesGroup.setVisible(v)
        self.modules._isVisible = v

    def cbEnergyLoss_clicked(self, enabled):
        self.location.setVisible(enabled)
        t = self.modules
        [t.setColumnHidden(i, not enabled) for i in range(3, 7)]
        t.update()

    def _addWidget(self, w, name, group=None,
                   horiz_stretch=False, vert_stretch=False):
        if group is None:
            group = QtWidgets.QGroupBox(name)
        ll = QtWidgets.QVBoxLayout()
        ll.setContentsMargins(1, 1, 1, 1)

        group.setLayout(ll)
        ll.addWidget(w)
        if not vert_stretch:
            ll.addStretch()
        self.inner.layout().addWidget(group, stretch=1 if horiz_stretch else 0)
        return group

    def saveState(self):
        config = self.preferences.saveState()
        config['modules'] = self.modules.saveState()
        config['locations'] = self.location.saveState()
        return config

    def toStr(self):
        return json.dumps(self.saveState(), indent=4) 

    def restoreState(self, config):
        if len(config):
            self.preferences.restoreState(config)
            self.modules.restoreState(config['modules'])
            self.location.restoreState(config['locations'])


class _StartThread(QtCore.QThread):

    def __init__(self):
        self.geolocator = None
        super().__init__()

    def run(self):
        # save startup time:
        from geopy.geocoders import Nominatim
        self.geolocator = Nominatim()


class _LocGroupBox(ButtonGroupBox):

    def __init__(self, name, parent=None, **kwargs):
        super().__init__(parent=parent, topleft=False, **kwargs)
        self.parent = parent
        self.btn.clicked.connect(lambda: parent.closeGroup(self))

        # only allow removing current group if there is at least one
        # other module group still there:
        def fn():
            gr = parent.groups
            if gr:
                gr[0].btn.setEnabled(len(gr) > 1)
            else:
                self.btn.setEnabled(False)

        self.btn.clicked.connect(fn)
        fn()

        self.btn.setIcon(QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.SP_TitleBarCloseButton))

        ltop = QtWidgets.QVBoxLayout()
        self.setLayout(ltop)
        lll = QtWidgets.QGridLayout()
        ltop.addLayout(lll)

        self.edName = QtWidgets.QLineEdit()
        self._oldLocName = name
        self.edName.setPlaceholderText(name)
        self.edName.textChanged.connect(self._edNameChanged)
        self.edAddress = QtWidgets.QLineEdit()
        self.edAddress.setPlaceholderText("7 Engineering Drive 1, Singapore")
        self.edAddress.returnPressed.connect(self._locationChanged)
        btn = QtWidgets.QPushButton("Lookup address")
        btn.clicked.connect(self._locationChanged)

        self._labFoundAddress = QtWidgets.QLabel()
#         self._labFoundAddress.setText("Found: ")

        lab1 = QtWidgets.QLabel("Latitude")
        lab2 = QtWidgets.QLabel("Longitude")

        self.edLong = QtWidgets.QLineEdit()
        self.edLong.setText('13.3765983')
        self.edLong.setValidator(QtGui.QDoubleValidator())

        self.edLat = QtWidgets.QLineEdit()
        self.edLat.setText('52.5094982')
        self.edLat.setValidator(QtGui.QDoubleValidator())

        lll.addWidget(self.edName, 0, 0)

        l2 = QtWidgets.QHBoxLayout()
        l2.addWidget(self.edAddress)
        l2.addWidget(btn)
        lll.addLayout(l2, 0, 1)

        lll.addWidget(self._labFoundAddress, 1, 0, 1, 3, QtCore.Qt.AlignRight)

        lll.addWidget(lab1, 2, 0)
        lll.addWidget(self.edLong, 2, 1)

        lll.addWidget(lab2, 3, 0)
        lll.addWidget(self.edLat, 3, 1)

        l6 = QtWidgets.QHBoxLayout()

        lll.addLayout(l6, 4, 1)

    def _edNameChanged(self, newname):
        self.parent.updateLocation(self._oldLocName, newname)
        self._oldLocName = newname

    def _locationChanged(self):
        loc = self.edAddress.text()
        if loc and self.parent._th.geolocator:
            location = self.parent._th.geolocator.geocode(loc)
            if location:
                self._labFoundAddress.setText(
                    location.address.replace(', ', '\n'))
                self.edLong.setText(str(location.longitude))
                self.edLat.setText(str(location.latitude))
            else:
                self._labFoundAddress.setText('')  
                self.edLong.setText('nothing')
                self.edLat.setText('nothing')


class _Location(ButtonGroupBox):

    def __init__(self, tabconfig):
        super().__init__("  Location")
        self.tabconfig = tabconfig
        self._th = _StartThread()
        self._th.start()

        ltop = QtWidgets.QVBoxLayout()
        self.setLayout(ltop)
        self.btn.setText("+")
        self.btn.clicked.connect(self.add)

        self.groups = []
        self.add()
        ltop.addStretch()

    def updateLocation(self, old, new):
        T = self.tabconfig.modules
        for row in range(T.rowCount()):
            i = T.item(row, 5)
            if i is not None and i.text() == old:
                i.setText(new)

    def closeGroup(self, g):
        self.groups.remove(g)
        g.close()

    def add(self):
        lg = len(self.groups)
        name = 'Loc%i' % (lg + 1)
        self._add(name)
        return name

    def _add(self, name):
        g = _LocGroupBox(name, parent=self)
        self.layout().insertWidget(len(self.groups), g)
        self.groups.append(g)
        return g

    def saveState(self):
        dd = {}
        for g in self.groups:
            loc = g.edName.text()
            if not loc:
                loc = g.edName.placeholderText()
            dd[loc] = (g.edAddress.text(), g.edLong.text(), g.edLat.text())
        return dd

    def restoreState(self, c):
        for g in self.groups:
            self.closeGroup(g)
        for name, (addr, long, lat) in c.items():
            g = self._add(name)
            g.edAddress.setText(addr)
            g.edLong.setText(str(long))
            g.edLat.setText(str(lat))


class _Delegate_ID(QtWidgets.QItemDelegate):

    def __init__(self, fn, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fn = fn

    def createEditor(self, parent, _styleitem, index):
        comboType = QtWidgets.QComboBox(parent)
        currentText = index.data()
        mods = self.fn()
        if currentText is not None:
            mods.insert(0, currentText)
        comboType.addItems(mods)
        return comboType


class _Delegate_typ(QtWidgets.QItemDelegate):

    def createEditor(self, parent, *_args, **_kwargs):
        comboType = QtWidgets.QComboBox(parent)
        comboType.addItems(['mSi', 'pSi', 'aSi', 'CdTe'])
        return comboType


class _Delegate_width(QtWidgets.QItemDelegate):

    def createEditor(self, parent, *_args, **_kwargs):
        editor = QtWidgets.QDoubleSpinBox(parent)
        editor.setRange(0.1, 3)
        return editor


class _Delegate_isc(QtWidgets.QItemDelegate):

    def createEditor(self, parent, *_args, **_kwargs):
        editor = QtWidgets.QDoubleSpinBox(parent)
        editor.setRange(0.1, 12)
        return editor


class _Delegate_tcoeff(QtWidgets.QItemDelegate):

    def createEditor(self, parent, *_args, **_kwargs):
        editor = QtWidgets.QDoubleSpinBox(parent)
        editor.setRange(0, 100)
        return editor


class _Delegate_ploss(QtWidgets.QItemDelegate):

    def createEditor(self, parent, *_args, **_kwargs):
        editor = QtWidgets.QDoubleSpinBox(parent)
        editor.setRange(0, 15)
        return editor


class _Delegate_loc(QtWidgets.QItemDelegate):

    def __init__(self, config, *args, **kwargs):
        self.tabconfig = config
        super().__init__(*args, **kwargs)

    def _getLocations(self):
        ll = self.tabconfig.location.groups
        return [l.edName.text() if l.edName.text()
                else l.edName.placeholderText() for l in ll]

    def createEditor(self, parent, *_args, **_kwargs):
        comboType = QtWidgets.QComboBox(parent)
        loc = self._getLocations()
        comboType.addItems(loc)
        return comboType


class _ModTable(Table):

    def __init__(self, config, gui):
        super().__init__(2, 7)
        self.tabconfig = config
        self.gui = gui

        [self.setColumnWidth(n, width)
         for n, width in enumerate([40, 50, 70, 70, 70, 50])]

        LABELS = ['ID\n', 'Width*\n[m]', "I_sc\n[A]", 'Power decline\n[%/a]',
                  'Typ\n', 'T_coeff\n[-%/°C]', 'Location\n']
        self.setHorizontalHeaderLabels(LABELS)

        # draw top header frame :
        header = self.horizontalHeader()
        header.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Plain)
        header.setLineWidth(1)
        self.setHorizontalHeader(header)
        # tooltips:
        headerItem = self.horizontalHeaderItem(1)
        headerItem.setToolTip(imageToHTML(
            IMG_HELP.join('hint_moduleSize.svg')))

        # save delegates, otherwise garbage collections causes crash
        # when multiple delegated are set via setItemDelegateForColumn
        self._delegates = (_Delegate_ID(self.remainingModules), _Delegate_width(),
                           _Delegate_isc(), _Delegate_ploss(), _Delegate_typ(),
                           _Delegate_tcoeff(), _Delegate_loc(self.tabconfig))
        [self.setItemDelegateForColumn(
            col, self._delegates[col]) for col in range(len(self._delegates))]

        self.verticalHeader().setVisible(False)
        h = self.horizontalHeader()
        h.setSectionResizeMode(h.Stretch)

        self.currentCellChanged.connect(self._addOrRemoveRows)

    def removeSelectedRows(self):
        super().removeSelectedRows()
        if not self.rowCount():
            self.setRowCount(1)

    def remainingModules(self):
        mod = self.gui.tabUpload.table.modules()
        for row in range(self.rowCount()):
            i = self.item(row, 0)
            if i is not None:
                try:
                    mod.remove(i.text())
                except KeyError:
                    pass
        return mod

    def checkValid(self):
        if not self._isVisible:
            return True
        # check whether all mod ids are entered:
#         nid = 0
        orow, xrow = [], []  # filled and empty cells (ID)
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item and item.text():
#                 nid += 1
                orow.append(row)
            else:
                xrow.append(row)
#         print(nid, len(self.gui.modules()), xrow)
        rmods = self.remainingModules()
        if len(rmods):
#         if nid != len(self.gui.modules()):
            self.gui.tabs.setCurrentWidget(self.tabconfig)
            items = []
            for row in xrow:
                item = self.setCell(row, 0)
                item.setBackground(QtGui.QBrush(QtCore.Qt.red))
                items.append(item)
            if len(rmods) > 1:
                txt = "Please add modules:\n\t%s" % str(rmods)[1:-1]
            else:
                txt = "Please add module:\n\t%s" % rmods
            QtWidgets.QMessageBox.critical(self, "ID column incomplete", txt)
            bg = QtWidgets.QTableWidgetItem().background()
            for item in items:
                item.setBackground(bg)
            return  False

        # check whether all other visible cells where a module id is defined as
        # filled
        items = []
        for row in orow:
            for c in range(1, self.columnCount()):
                if not self.isColumnHidden(c):
                    item = self.setCell(row, c)
                    if not item.text():
                        items.append(item)
                        item.setBackground(QtGui.QBrush(QtCore.Qt.red))
        if items:
            self.gui.tabs.setCurrentWidget(self.tabconfig)
            QtWidgets.QMessageBox.critical(self, "ID parameter incomplete",
                                           "Please fill in all parameters")
            bg = QtWidgets.QTableWidgetItem().background()
            for item in items:
                item.setBackground(bg)
            return False

        return True

    def _addAllMissingModules(self):
        mod = self.remainingModules()
        self.setRowCount(self.rowCount() + len(mod))
        row = -1
        for m in mod:
            while True:
                row += 1
                i = self.item(row, 0)
                if i is None or i.text() == '':
                    break
            self.setCell(row, 0, m)
                    
    def mousePressEvent(self, event):
        mouseBtn = event.button()
        if mouseBtn == QtCore.Qt.RightButton:
#             self._menu = QMenu() 
            
            col = self.columnAt(event.pos().x())
            self._menu = self.createContextMenu()
            if col == 0:
                self._menu.addAction("Add missing modules").triggered.connect(
                    self._addAllMissingModules)
            else:
                row = self.rowAt(event.pos().y())
                self._rclickedCell = self.item(row, col)
                
                self._menu.addAction("Apply for all").triggered.connect(
                    self._applyForAll)

            self._menu.popup(event.globalPos())
        super().mousePressEvent(event)

    def _applyForAll(self):
        if self._rclickedCell:
            txt = self._rclickedCell.text()
            col = self.currentColumn()
            for row in range(self.rowCount()):
                self.setCell(row, col, txt)

    def _addOrRemoveRows(self, row):
        if row == self.rowCount() - 1:
            self.setRowCount(row + 2)
        else:
            for r in range(self.rowCount() - 1, row + 1, -1):
                empty = True
                for col in range(self.columnCount()):
                    item = self.item(r, col)
                    if item is not None and item.text():
                        empty = False
                if empty:
                    self.setRowCount(r)

    def saveState(self):
        state = {}
        for row in self.toTable():
            state[row[0]] = row[1:]
        return state

    def restoreState(self, tabledict):
        table = []
        for mod in sorted(tabledict.keys()):
            row = [mod]
            row.extend(tabledict[mod])
            table.append(row)
        self.pasteTable(table)


class _GroupBox(QtWidgets.QGroupBox):

    # make title bold
    def __init__(self, title):
        super().__init__(title)
        self.setStyleSheet('''QGroupBox {font-weight: bold;}''')


class _Preferences(QtWidgets.QWidget):

    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        ll = QtWidgets.QVBoxLayout()
        self.setLayout(ll)

        g0 = _GroupBox('General')
        g1 = _GroupBox('Camera calibration')
        self.gCor = g = _GroupBox('Image correction (free)')
        self.gPP = g2 = _GroupBox(
            'PRO features%s' % (' (%s)' % gui.server.pricePROfeatures() if gui else ''))

        ll.addWidget(g0)
        ll.addWidget(g1)
        ll.addWidget(g)
        ll.addWidget(g2)
        ll.addStretch()

        g.setCheckable(True)
        g.setChecked(True)
#         g.toggled.connect(self._correctToggled)

        # <<<<GENERAL SECTION
        lab = QtWidgets.QLabel(" File viewer")
        self.cbViewer = cb = QtWidgets.QComboBox()
        cb.addItems(("Inline", "OS default", 'dataArtist'))
        l0 = QtWidgets.QVBoxLayout()
        l01 = QtWidgets.QHBoxLayout()
        l01.addWidget(cb)
        l01.addWidget(lab)
        l01.addStretch()

        self._cb2fa = QtWidgets.QCheckBox('2 factor authorization')
        self._cb2fa.setToolTip("""Keep checked to receive an authorization code every time you login,
Be aware that although switching option off will save you time, your account can be easily 
taken over by everyone who has your password.""")
        if gui:
            self._cb2fa.setChecked(gui.server.requires2FA())
            self._cb2fa.clicked.connect(gui.server.setRequires2FA)

        autologin = QtWidgets.QCheckBox('Auto-login last user')
        if gui:
            self._filePwd = gui.PATH_USER.join('pwd')
            self._cb2fa.setToolTip("""If checked, user password will saved in %s. 
The last user will automatically logged in at every new start, 
until this option is switched off.""" % self._filePwd)
            autologin.setChecked(self._filePwd.exists())
            if autologin.isChecked():
                self._cb2fa.setEnabled(False)
        autologin.clicked.connect(self._changeAutologin)

        g0.setLayout(l0)
        l0.addLayout(l01)
        l0.addWidget(self._cb2fa)
        l0.addWidget(autologin)

        # <<<CAMERA SECTION:
        l1 = QtWidgets.QVBoxLayout()
        l11 = QtWidgets.QHBoxLayout()
        l1.addLayout(l11)

        g1.setLayout(l1)

        # CAMERA NAME
        cb = self.camOpts = QtWidgets.QComboBox()
        if gui:
            cb.addItems(gui.server.cameraList())
        cb.setEditable(True)
        cb.setMinimumWidth(135)
        cb.lineEdit().setValidator(PNameValidator())
        cb.currentIndexChanged.connect(self._renameCameraStarted)
        cb.setInsertPolicy(QtWidgets.QComboBox.InsertAtCurrent)

        self._lastCamName = cb.currentText()
        cb.lineEdit().editingFinished.connect(self._renameCamera)

        btnDel = QtWidgets.QToolButton()
        btnDel.setText('-')
        btnDel.setAutoRaise(True)
        btnDel.clicked.connect(self._removeCurrentCamera)
            
        btnAdd = QtWidgets.QToolButton()
        btnAdd.setText('+')
        btnAdd.setAutoRaise(True)
        btnAdd.clicked.connect(self._newCamera)

        self.cbCamUpdate = QtWidgets.QCheckBox("Update")
        txt = """Check this box, to update 
camera calibration using images from current upload agenda."""
        self.cbCamUpdate.setToolTip(txt)
        self.cbCamUpdate.setChecked(True)

        ckCal = QtWidgets.QCheckBox('Use own camera calibration')
        ckCal.setToolTip(''''By default a camera calibration is generated by the images 
provided and no camera calibration is needed. However, the quality of camera correction can possibly be increased 
if an camera calibration is conducted. Check this box to use your own calibration as obtained with dataArtist''')
        # FIXME: make upload of own calibrations possible
        ckCal.clicked.connect(lambda _: [QtWidgets.QMessageBox.warning(
            self, 'Not implemented', 'At the moment it is not possible to use an own camera calibration. Sorry.'
        ), ckCal.setChecked(False), ckCal.setEnabled(False)])

        self._btnCamReport = QtWidgets.QPushButton('View report') 
        self._btnCamReport.setToolTip('Click  to view latest camera calibration report')
        self._btnCamReport.setFlat(True) 
        self._btnCamReport.clicked.connect(self._displayCurrentCameraReport)        
#         if gui:
#             self.camOpts.currentTextChanged.connect(self._checkCamReportAvail)
#             self._checkCamReportAvail()

        self.ckLight = QtWidgets.QCheckBox("Variable light conditions")
        txt = """Check this box, if measurements are NOT done in a light-tight chamber
or the environmental light conditions change in every measurement 
(e.g. outdoor measurements).
If your background images look like this ...%s 
You can uncheck this box.
If however you background images look like this... %s 
You should ensure, that light does not change
during measurements.

If this option is checked, no background calibration will be generated.
Therefore for background correction at least one background 
image for every measurement is essential.""" % (
              imageToHTML(IMG_HELP.join('bg_noStraylight.jpg')),
              imageToHTML(IMG_HELP.join('bg_straylight.jpg')))
        self.ckLight.setToolTip(toHtml(txt))

        l11.addWidget(self.camOpts)
        l11.addWidget(btnDel)
        l11.addWidget(btnAdd)
        l11.addWidget(self._btnCamReport)
        l11.addStretch()
        l1.addWidget(self.cbCamUpdate)
        l1.addWidget(ckCal)
        l1.addWidget(self.ckLight)

        # <<<<CORRECT IMAGES SECTION
        lll = QtWidgets.QVBoxLayout()
        g.setLayout(lll)

#         g2.setCheckable(True)
#         g2.setChecked(False)
#         g2.toggled.connect(self._postProcessingToggled)

        lll2 = QtWidgets.QVBoxLayout()
        g2.setLayout(lll2)

        self.cbSize = QtWidgets.QCheckBox("Fixed output size")
        self.cbSize.setToolTip(
            '''If this parameter is not checked, 
image size of the corrected image will be determined according to input image''')
        self.sizeX = QtWidgets.QSpinBox()
        self.sizeX.setPrefix('x: ')
        self.sizeX.setRange(0, 20000)
        self.sizeX.setValue(4000)
        self.sizeX.setSuffix(' px')
        self.sizeX.setEnabled(False)

        self.sizeY = QtWidgets.QSpinBox()
        self.sizeY.setPrefix('y: ')
        self.sizeY.setRange(0, 20000)
        self.sizeY.setValue(2400)
        self.sizeY.setSuffix(' px')

        self.sizeY.setEnabled(False)

        self.cbSize.clicked.connect(self.sizeX.setEnabled)
        self.cbSize.clicked.connect(self.sizeY.setEnabled)

        lSize = QtWidgets.QHBoxLayout()
        lSize.addWidget(self.cbSize)
        lSize.addWidget(self.sizeX)
        lSize.addWidget(self.sizeY)
        lSize.addStretch(1)
        
        labCamcor = QtWidgets.QLabel("Correct camera distortion")
        self.corCam = QtWidgets.QComboBox()
        self.corCam.addItems(['strong', 'weak', 'off'])
        self.corCam.setToolTip('''<b>strong</b> --> CALIBRATE and CORRECT for the following distortions:
    - vignetting = f(f-number)
    - dark current =  f(exposure time, ISO, f-number)
    - lens distortion 
    - noise = f(ISO)
    - camera response function = f(ISO)
    - single time effects (if 2 sequential images are available)
    - image artifacts (high gradient defects)
    - sensor sensitivity (spatial)

    PRO: returns highest quality output
    CON: time consuming
    
<hr>

<b>weak</b> --> ESTIMATE and CORRECT for the following distortions:
    - average dark current level
    - vignetting from single image 

    PRO: much faster than [strong]
    CON: no camera calibration and no calibration report generated
         returns lower quality images
         
<hr> 
       
<b>off</b> --> no correction for camera induced distortions

    PRO: fastest method
    CON: resulting images can be highly distorted
'''.replace('\n', '<br>').replace(' ', '&nbsp;'))
        labCamcor.setToolTip(self.corCam.toolTip())

        lCam = QtWidgets.QHBoxLayout()
        lCam.addWidget(labCamcor)
        lCam.addWidget(self.corCam)
        lCam.addStretch(1)

        self.cbDeformed = QtWidgets.QCheckBox("Devices might be deformed")
        self.cbDeformed.setToolTip('''Check this parameter, 
if mechanical deformation of the imaged device cannot be ruled out.''')

        self.cbPos = QtWidgets.QCheckBox(
            "Device position changes during measurement")
        self.cbPos.setToolTip(
            '''Check this parameter, 
if the device position differs for different currents in one measurement.''')

        # TODO: should be always done, or?
#         self.cbPrecise = QtWidgets.QCheckBox("Precise alignment")
#         self.cbPrecise.setToolTip('This option increases calculation time')
#         self.cbPrecise.setChecked(True)

        self.comAlignment = QtWidgets.QComboBox()
        self.comAlignment.addItems(['strong', 'medium', 'weak', 'off'])
        self.comAlignment.setCurrentText('medium')
        self.corCam.setToolTip('''Due to module deformation of remaining optical distortion,
images of the same devices at different measurements might remain miss-aligned, even after perspective correction.
Its reduction quality influences the overall calculation speed.
        
        <b>strong</b> --> Image alignment will be most precise,  but computation takes longest.
        <b>median</b> --> Image alignment will be precise,  but computation takes some time.
        <b>weak</b> --> Image alignment will be less precise,  but computation is faster.
        <b>off</b> --> NO image alignment.
        ''')

        lAlign = QtWidgets.QHBoxLayout()
        lAlign.addWidget(QtWidgets.QLabel('Alignment precision'))
        lAlign.addWidget(self.comAlignment)
        lAlign.addStretch(1)

        self.cbArtifacts = QtWidgets.QCheckBox("Remove artifacts")
        self.cbArtifacts.setToolTip('Filter erroneous pixels')
        self.cbArtifacts.setChecked(True)

        lcorr = QtWidgets.QHBoxLayout()
        lcorrW = QtWidgets.QVBoxLayout()
        lcorr.addLayout(lcorrW)
        lcorrW.addLayout(lSize)

        lcorrW.addLayout(lCam)

        lcorrW.addWidget(self.cbDeformed)
        lcorrW.addWidget(self.cbPos)
        lcorrW.addLayout(lAlign)
        lcorrW.addWidget(self.cbArtifacts)

        # <<<<POSTPROCESSING SECTION
        self.cbPost = QtWidgets.QCheckBox("Post processing")

        self.cbQual = cb0 = QtWidgets.QCheckBox(
            "Image quality")
        cb0.toggled.connect(lambda checked: self.corCam.setCurrentIndex(0) if checked else None)
        cb0.setChecked(False)

        self.cbUncert = cb01 = QtWidgets.QCheckBox("Map uncertainty")

        self.cbEnhance = QtWidgets.QCheckBox(
            "Enhance image (sharpen, denoise)")
        self.cbEnhance.setToolTip(
            'Create an additional sharpened and denoised image')

        self.cbTimelapse = QtWidgets.QCheckBox("Create timelapse video")
        self.cbTimelapse.setToolTip('TODO')

        self.cbStats = QtWidgets.QCheckBox("Cell statistics")
        self.cbStats.setToolTip(
            'Calculate cell average and standard deviation')

        self.cbFeatures = cb12 = QtWidgets.QCheckBox("Feature detection")
        cb12.setToolTip(
            'Detect and measure cracks and inactive areas')

        self.cbPerf = cb1 = QtWidgets.QCheckBox("Estimate Power loss")
        cb1.setToolTip(
            'Calculate the power loss relative to initial measurement')

        self.cbEnergyLoss = cb11 = QtWidgets.QCheckBox("+ Energy loss")
        self._makeCBdependant(cb1, cb11)

        self.cbReport = QtWidgets.QCheckBox(
            "PDF report")

        self.cbMail = QtWidgets.QCheckBox("Send report via mail")

        self._makeCBdependant(cb0, cb01)
        self._makeCBdependant(cb0, self.cbEnhance)

        self._makeCBdependant(self.cbPost, self.cbStats)
        self._makeCBdependant(self.cbPost, self.cbTimelapse)
        self._makeCBdependant(self.cbPost, self.cbFeatures)
        self._makeCBdependant(self.cbPost, self.cbPerf)

        lll.addLayout(lcorr)
        lll2.addWidget(cb0)

        self._addIndented(lll2, cb01)
        self._addIndented(lll2, self.cbEnhance)

        # add post proc
        lll2.addWidget(self.cbPost)
        self._addIndented(lll2, self.cbStats)
        self._addIndented(lll2, self.cbTimelapse)
        self._addIndented(lll2, cb12)
        self._addIndented(lll2, cb1)
        self._addIndented(lll2, cb11, 2)
        
        self.cbManual = cb2 = QtWidgets.QCheckBox(
            "Ask us to evaluate the results")

        self.manualEditor = editor = QtWidgets.QTextEdit()
        editor.setPlaceholderText(
            "Problem description\nFurther instructions\netc.")
        editor.hide()  # setEnabled(False)
        cb2.clicked.connect(editor.setVisible)

        lll2.addWidget(self.cbReport)
        self._addIndented(lll2, self.cbMail)
        self._addIndented(lll2, cb2)
        self._addIndented(lll2, editor)

        self._makeCBdependant(self.cbReport, self.cbMail)
        self._makeCBdependant(self.cbReport, self.cbManual)

#     def _checkCamReportAvail(self):
#         cam = self.camOpts.currentText()
#         self._btnCamReport.setEnabled(
#             self.gui.server.cameraReportAvailable(cam))

    def _removeCurrentCamera(self):
        cam = self.camOpts.currentText()
        ret = QtWidgets.QMessageBox.warning(self, 'Removing calibration for camera <%s>' % cam,
            'Are you sure?')
        if ret == QtWidgets.QMessageBox.Ok:
            success = self.gui.server.cameraReportAvailable(cam)

    def _displayCurrentCameraReport(self):
        cam = self.camOpts.currentText()
        if not self.gui.server.cameraReportAvailable(cam):
            QtWidgets.QMessageBox.warning(self, 'Not available',
            'No PDF report available for the chosen camera. Calibrate first!')
        else:
            local = self.gui.root.mkdir('cameras').join(cam + '.pdf')
            self.gui.addDownload(cam, local, os.startfile, cmd='downloadCameraReport(%s)' % cam)

    def _changeAutologin(self, enable):
        if not enable:
            if self._filePwd.exists():
                self._filePwd.remove()
        else:
            self._cb2fa.setChecked(False)
            self._cb2fa.setEnabled(False)

            if self.gui.pwd is None:
                self.gui.pwd = QtWidgets.QInputDialog.getText(self, 'Re-enter password',
                                                              'Please enter you password again')

            with open(self._filePwd, 'wb') as f:
                # this is obviously not a save way to store a password,
                # but for decrypting, the villain has to know some python
                # and has to find this code
                encrypted = base64.b64encode(self.gui.pwd.encode())
                f.write(encrypted)

    def _newCamera(self):
        f = FilenameInputDialog('New camera', 'Name:')
        f.exec_()
        if f.result() == f.Accepted:
            self.camOpts.addItem(f.text())
            self.camOpts.setCurrentIndex(self.camOpts.count() - 1)

#     def _postProcessingToggled(self, checked):
#         if not checked:
#             if self.cbPerf.isChecked():
#                 self.cbPerf.toggle()
#             if self.cbQual.isChecked():
#                 self.cbQual.toggle()
                
    def _renameCameraStarted(self):
        self._lastCamName = self.camOpts.currentText()

    def _renameCamera(self):
        new = self.camOpts.currentText()
        new2 = self.gui.server.cameraRename(self._lastCamName, new)
        self._lastCamName = new2
        if new != new2:
            self.camOpts.setCurrentText(new2)

    @staticmethod
    def _makeCBdependant(cbparent, cb):
        '''
        disable/uncheck <cb> is <parentcb> is unchecked
        '''
        cb.setEnabled(cbparent.isChecked())

        def fn(checked):
            if not checked:
                cb.setChecked(False)
            cb.setEnabled(checked)

        cbparent.toggled.connect(lambda checked: fn(checked))

    def _addIndented(self, layout, widget, nindent=1):
        ll = QtWidgets.QHBoxLayout()
        ll.addSpacing(20 * nindent)
        ll.addWidget(widget)
        layout.addLayout(ll)

    def saveState(self):
        return {'calibrate':{'update':self.cbCamUpdate.isChecked(),
                             'variable_light_conditions': self.ckLight.isChecked(),
                             'camname': self.camOpts.currentText()},
                'correct':{'level':2 - self.corCam.currentIndex(),
                           'calc_quality': self.cbQual.isChecked(),
                           'calc_uncertainty': self.cbUncert.isChecked(),
                           'fixed_output_size': self.cbSize.isChecked(),
                           'output_image_size': (self.sizeY.value(), self.sizeX.value()),
                           'module_is_deformed': self.cbDeformed.isChecked(),
                           'device_at_same_pos_for_diff_currents': self.cbPos.isChecked(),
#                            'sub_px_alignment': self.cbPrecise.isChecked(),
                           'alignment_precission':self.comAlignment.currentText(),
                           'removeArtefacts': self.cbArtifacts.isChecked(),
                           'enhance_image': self.cbEnhance.isChecked()},
                'post':{
                        'features': self.cbFeatures.isChecked(),
                        'statistics': self.cbStats.isChecked(),
                        'timelapse':self.cbTimelapse.isChecked(),
                        'ploss': self.cbPerf.isChecked(),
                        'eloss': self.cbEnergyLoss.isChecked()},
                'setup':{'correct':self.gCor.isChecked(),
                         'post': self.cbPost.isChecked(),
                         'manual_check': self.cbManual.isChecked(),
                         'comments': self.manualEditor.toPlainText(),
                         'report': self.cbReport.isChecked(),
                         'report_via_mail': self.cbMail.isChecked()}}

    def restoreState(self, c):  
        cc = c['correct']
        self.cbQual.setChecked(cc['calc_quality'])
        self.corCam.setCurrentIndex(2 - cc['level'])
        self.cbUncert.setChecked(cc['calc_uncertainty'])
        self.cbSize.setChecked(cc['fixed_output_size'])
        self.sizeX.setValue(cc['output_image_size'][1])
        self.sizeY.setValue(cc['output_image_size'][0])
        self.cbDeformed.setChecked(cc['module_is_deformed'])
        self.cbPos.setChecked(cc['device_at_same_pos_for_diff_currents'])
        self.comAlignment.setCurrentText(cc['alignment_precission'])
        self.cbArtifacts.setChecked(cc['removeArtefacts'])
        self.cbEnhance.setChecked(cc['enhance_image'])
        cc = c['post']        
        self.cbStats.setChecked(cc['statistics'])
        self.cbTimelapse.setChecked(cc['timelapse'])
        self.cbFeatures.setChecked(cc['features'])
        self.cbPerf.setChecked(cc['ploss'])
        self.cbEnergyLoss.setChecked(cc['eloss'])
        cc = c['setup'] 
        self.gCor.setChecked(cc['correct'])
        self.cbPost.setChecked(cc['post'])            
        self.cbReport.setChecked(cc['report'])
        self.cbMail.setChecked(cc['report_via_mail'])
        self.cbManual.setChecked(cc['manual_check'])
        self.manualEditor.setPlainText(cc['comments'])
        cc = c['calibrate']  
        self.cbCamUpdate.setChecked(cc['update'])
        self.ckLight.setChecked(cc['variable_light_conditions'])
        self.camOpts.setCurrentText(cc['camname'])

#         cc0 = c['correct']
#         PRO = True in c['post'].values() or \
#               True in c['setup'].values() or \
#               True in (cc0['enhance_image'], cc0['calc_uncertainty'], cc0['calc_quality'])
#         self.gPP.setChecked(PRO)


if __name__ == '__main__':
    from client.Application import Application
    
    app = Application()

    w = TabConfig(None)
    w.resize(1100, 600)

#     w.restore(w.config())

    w.show()
    app.exec_()
