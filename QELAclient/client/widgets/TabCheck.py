# -*- coding: utf-8 -*-
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui

from fancytools.utils import json2 as json

# local
from client.communication.utils import agendaFromChanged
from client.widgets.Contact import Contact
from client.widgets.GridEditor import CompareGridEditor
from client.widgets._Base import QMenu
import client


class QTreeWidget(QtWidgets.QTreeWidget):

    def getAffectedItems(self):
        '''return list of all items in currently selected tree
        e.g.:
        Ia
            IIa <-- selected
                IIIa
        Ib
            IIb
                IIIb

        returns [Ia,IIa,IIIa]
        '''
        out = []

        def _fn(item):
            ii = item.childCount()
            if ii:
                # go down to last child
                for i in range(ii):
                    ch = item.child(i)
                    _fn(ch)
            else:
                # build list [topitem, child, childchild...]
                out.append(item)

        _fn(self.currentItem())
        return out

    def recursiveItemsText(self, item=None, col=0):
        # TODO: if practically recursiveItems but with text instead of
        # items ... shorten
        if item is None:
            item = self.invisibleRootItem()
        for i in range(item.childCount()):
            ch = item.child(i)
            yield from self.recursiveItemsText(ch, col)
        if item != self.invisibleRootItem():
            out = self.itemInheranceText(item)
            yield (item, out)

    @staticmethod
    def itemInherence(item):
        out = [item]
        while True:
            p = item.parent()
            if not p:
                break
            out.insert(0, p)
            item = p
        return out

    @classmethod
    def itemInheranceText(cls, item, col=0):
        return [i.text(col) for i in cls.itemInherence(item)]

    @staticmethod
    def findChildItem(parent, name, col=0):
        for i in range(parent.childCount()):
            if parent.child(i).text(col) == name:
                return parent.child(i)

    def buildCheckTree(self, item=None, nintent=0):
        """
        output:
            [(ID0,0,{...}),(meas0,1),(cur0,2,{...}),(cur1,2,{...}),...]
        """
        if item is None:
            item = self.invisibleRootItem()
        for i in range(item.childCount()):
            ch = item.child(i)
            yield from self.buildCheckTree(ch, nintent + 1)
        if item != self.invisibleRootItem():
            yield (item, nintent - 1)


class TabCheck(QtWidgets.QSplitter):
    '''Nobody is perfect. Although our image processing routines are fully automated,
    they can sometimes fail to precisely detect a solar module. Especially for
    uncommon module types or low quality images your help for verify or alter our results
    can be needed. This tab displays results from camera and perspective correction
    of all EL images in your current project. In  here,  images are highly compressed
    to  reduce download times. 
    
    As soon as new results are available,  this tab will be highlighted.
    Please take your time to go through the results. You can verify of change:
        * Position of the four module corners.
        * Position of the bottom left corner
        * Number of horizontal/vertical cells and busbars.
    After clicking on <Submit changes> all images modified by you will be processed again.
    Manual verification increases quality of the generated module report.
    Please inform  us, if you find odd or erroneous results. For this click  on 
            Actions -> Report a problem
    '''

    def __init__(self, gui=None):
        super().__init__()

        self.gui = gui
        self.vertices_list = []
        self._lastP = None

        self._grid = CompareGridEditor()
        self._grid.gridChanged.connect(self._updateGrid)
#         self._grid.cornerChanged.connect(self._updateCorner)
        self._grid.verticesChanged.connect(self._updateVertices)

        self.btn_markCurrentDone = QtWidgets.QPushButton("Mark verified")
        self.btn_markCurrentDone.setToolTip('''Confirm  that detected module position and type are correct. 
As soon as all modules are verified, click on <Submit> to inform our server.''')
        self.btn_markCurrentDone.clicked.connect(self._toggleVerified)

        self._grid.bottomLayout.addWidget(self.btn_markCurrentDone, 0, 0)

        self.list = QTreeWidget()
        self.list.setHeaderHidden(True)
        self.list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(lambda pos: self._menu.popup(pos))

        btnSubmit = QtWidgets.QPushButton('Submit')
        btnSubmit.setToolTip('''Submit all changes to  the server. 
Correct results will  be marked as 'verified' in the module report and modified result will be 
processed again.''')
        btnSubmit.clicked.connect(self._acceptAll)

        llist = QtWidgets.QHBoxLayout()
        llist.addStretch()
        llist.addWidget(btnSubmit)

        l3 = QtWidgets.QVBoxLayout()
        l3.addLayout(llist)
        l3.addWidget(self.list)

        btn_actions = QtWidgets.QPushButton("Actions")
        self._menu = menu = QMenu()
        menu.aboutToShow.connect(self._showMenu)

        m = menu.addMenu('All')
        a = m.addAction("Reset changes")
        a.setToolTip('Reset everything to the state given by the server.')
        a.triggered.connect(self._resetAll)

        a = m.addAction("Recalculate all measurements")
        a.setToolTip('''Choose this option to run image processing on all submitted images
of the selected module again. This is useful, since QELA image processing routines are continuously developed
and higher quality results can be available. Additionally, this option will define a new 
template image (the image other images are perspectively aligned to) depending on the highest resolution/quality  
image within the image set.''')
        a.triggered.connect(self._processAllAgain)

        a = menu.addAction("Reset changes")
        a.setToolTip('Reset everything to the state given  by the server.')
        a.triggered.connect(self._resetChanges)

        a = menu.addAction("Report a problem")
        a.setToolTip('Write us a mail and inform us on the problem you experience.')
        a.triggered.connect(self._reportProblem)
        
        a = menu.addAction("Upload images again")
        a.setToolTip('Click this button to  upload and process the images of the selected measurement again.')
        a.triggered.connect(self._uploadAgain)
        
        self._aRemove = a = menu.addAction("Remove measurement")
        a.setToolTip('Remove the current measurement/device from the project. This includes all corresponding data. Pleas write us a mail, to undo this step.')
        a.triggered.connect(self._removeMeasurement)

        btn_actions.setMenu(menu)
        l3.addWidget(btn_actions)

        wleft = QtWidgets.QWidget()
        wleft.setLayout(l3)

        self.btnCollapse = QtWidgets.QPushButton(wleft)
        self.btnCollapse.setIcon(QtGui.QIcon(
            client.MEDIA_PATH.join('btn_toggle_collapse.svg')))
        self.btnCollapse.toggled.connect(self._toggleExpandAll)
        self.btnCollapse.setCheckable(True)
        self.btnCollapse.setFlat(True)
        self.btnCollapse.resize(15, 15)
        self.btnCollapse.move(7, 15)
        header = QtWidgets.QLabel('ID > Meas > Current', wleft)
        header.move(25, 7)

        self.addWidget(wleft)
        self.addWidget(self._grid)

        self.list.currentItemChanged.connect(self._loadImg)

        if self.gui is not None:
            self._timer = QtCore.QTimer()
            self._timer.setInterval(5000)
            self._timer.timeout.connect(self.checkUpdates)
            self._timer.start()
         
    def saveState(self):
        
        try:
            ID, meas, cur, typ = self._getIDmeasCur()
        except AttributeError:  # no items
            ll = []
        else:
            if typ == 'device':
                ll = [ID.text(0)]
            elif typ == 'measurement':
                ll = [ID.text(0), meas.text(0)]
            else:
                ll = [ID.text(0), meas.text(0), cur.text(0)]

        return {'expanded':self.btnCollapse.isChecked(),
                'selected':ll}
 
    def restoreState(self, state):
        self.btnCollapse.setChecked(state['expanded'])
        self._selectFromName(state['selected'])

    def _selectFromName(self, ll):
        if ll:
            root = self.list.invisibleRootItem()
            
            def fn(name, parent, ll):  # try to select item by listed name ll=[ID,meas,current]
                for i in range(parent.childCount()):
                    child = parent.child(i)
                    if child.text(0) == name:
                        if ll:
                            return fn(ll.pop(0), child, ll)
                        else:
                            self.list.setCurrentItem(child)
    
            fn(ll.pop(0), root, ll)                    

    def _toggleExpandAll(self, checked):
        if checked:
            self.list.expandAll()
        else:
            self.list.collapseAll()
            
    def _showMenu(self):
        self._aRemove.setText('Remove %s' % self._getIDmeasCur()[-1])

    def _processAllAgain(self):
        # TODO
        reply = QtWidgets.QMessageBox.question(
            self, 'TOD:', "This option is not available at the moment, SORRY",
            QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

    def _uploadAgain(self):
        items = self.list.getAffectedItems()
        lines = []
        for item in items:
            data = item.data(1, QtCore.Qt.UserRole)

            agenda = self.gui.PATH_USER.join(
                'upload', data['timestamp'] + '.csv')
            lines.extend(agendaFromChanged(agenda, data))

        self.gui.tabUpload.dropLines(lines)

    def _getAffectedPaths(self):
        items = self.list.getAffectedItems()
        out = []
        for item in items:
            p = item.parent()
            pp = p.parent()
            out.append("%s\\%s\\%s" % (
                pp.text(0), p.text(0), item.text(0)))
        return out

    def _removeMeasurement(self):
        affected = self._getAffectedPaths()
        if affected:
            box = QtWidgets.QMessageBox()
            box.setStandardButtons(box.Ok | box.Cancel)
            box.setWindowTitle('Remove measurement')
            box.setText("Do you want to remove ...\n%s" % "\n".join(affected))
            box.exec_()

            if box.result() == box.Ok:
                res = self.gui.server.removeMeasurements(*affected)
                if res != 'OK':
                    QtWidgets.QMessageBox.critical(self, 'Error removing measurements', res)
                else:
                    item = self.list.currentItem()
                    parent = item.parent()
                    if  parent is None:
                        parent = self.list.invisibleRootItem()
                    parent.removeChild(item)

#                 self.checkUpdates()

    def _reportProblem(self):
        ID, meas, cur = self._getIDmeasCur()[:-1]
        self._contact = Contact(self.gui)
        self._contact.subject.setText('%s\\%s\\%s' % (
            ID.text(0), meas.text(0), cur.text(0)))
        self._contact.editor.text.setText(
            'E.g. bad image correction, \n   remaining vignetting, \n   image looks distorted')
        self._contact.show()

    def _resetAll(self):
        reply = QtWidgets.QMessageBox.question(
            self, 'Resetting all changes', "Are you sure?",
            QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            self._resetChanges(self.list.invisibleRootItem())

    def _resetChangesCurrentItem(self):
        item = self.list.currentItem()
        return self._resetChanges(item)

    def _excludeUnchangableKeys(self, data):
        if 'vertices' in data:
            return {k: data[k] for k in ['verified', 'vertices']}
        return data

    def _resetChanges(self, item):
        if type(item) is bool:
            item = self.list.currentItem()

        def _reset(item):
            data = item.data(1, QtCore.Qt.UserRole)
            if data is not None:
                item.setData(0, QtCore.Qt.UserRole,
                             self._excludeUnchangableKeys(data))

            f = item.font(0)
            f.setBold(False)
            item.setFont(0, f)

            for i in range(item.childCount()):
                _reset(item.child(i))

        _reset(item)

        cur = self._getIDmeasCur()[2]
        data = cur.data(0, QtCore.Qt.UserRole)
        self._grid.grid.setVertices(data['vertices'])

        self._changeVerifiedColor(item)

    def _isIDmodified(self, ID):
        data0 = ID.data(0, QtCore.Qt.UserRole)
        data1 = ID.data(1, QtCore.Qt.UserRole)
        return (data0['nsublines'] != data1['nsublines']
                or data0['grid'] != data1['grid'])

    def _updateVertices(self, vertices):
        cur = self._getIDmeasCur()[2]

        data = cur.data(1, QtCore.Qt.UserRole)
        originalvertices = data['vertices']
        data['vertices'] = vertices
        cur.setData(0, QtCore.Qt.UserRole, data)

        changed = not np.allclose(
            vertices, np.array(originalvertices), rtol=0.01)

        f = cur.font(0)
        f.setBold(changed)
        cur.setFont(0, f)

    def _updateGrid(self, key, val):
        ID = self._getIDmeasCur()[0]
        # update data:
        data = ID.data(0, QtCore.Qt.UserRole)
        data[key] = val
        ID.setData(0, QtCore.Qt.UserRole, data)
        # font -> bold 
        f = ID.font(0)
        changed = self._isIDmodified(ID)
        f.setBold(changed)
        ID.setFont(0, f)
#         # grid is identical for all current and measurements of one device, so
#         # update other items:
#         for i in range(ID.childCount()):
#             meas = ID.child(i)
#             for j in range(meas.childCount()):
#                 current = meas.child(j)

    def _getIDmeasCur(self):
        '''
        returns ID, meas, cur, typ
        of current item index(0...id,1...meas,2...current)
        '''
        item = self.list.currentItem()
        p = item.parent()
        if p is not None:
            pp = p.parent()
            if pp is not None:  # item is current
                ID, meas, cur = pp, p, item
                index = 'current'
            else:  # item is measurement
                ID, meas, cur = p, item, item.child(0)
                index = 'measurement'
        else:  # item is ID
            ID, meas, cur = (item, item.child(0),
                             item.child(0).child(0))
            index = 'device'
        return ID, meas, cur, index

    def _loadImg(self):
        if not self.list.currentItem():
            return
        try:
            ID, meas, cur = self._getIDmeasCur()[:-1]
            txt = ID.text(0), meas.text(0), cur.text(0)
            root = self.gui.projectFolder()
            p = root.join(*txt)
            if p == self._lastP:
                return
            self._lastP = p

            p0 = p.join(".prev_A.jpg")
            p1 = p.join(".prev_B.jpg")
            ll = len(root) + 1
            if not p0.exists():
                self.gui.server.download(p0[ll:], root.join(p0[ll:]))
            if not p1.exists():
                self.gui.server.download(p1[ll:], root.join(p1[ll:]))

            self._grid.readImg1(p0)
            self._grid.readImg2(p1)

            # load/change grid
            idata = ID.data(0, QtCore.Qt.UserRole)
            cells = idata['grid'][::-1]
            nsublines = idata['nsublines']

            cdata = cur.data(0, QtCore.Qt.UserRole)
            vertices = cdata['vertices']

            # TODO: remove different conventions
#             vertices = np.array(vertices)[np.array([0, 3, 2, 1])]

            self._grid.grid.setNCells(cells)
            self._grid.grid.setVertices(vertices)

            self._grid.edX.setValue(cells[0])
            self._grid.edY.setValue(cells[1])
            self._grid.edBBX.setValue(nsublines[1])
            self._grid.edBBY.setValue(nsublines[0])
            self._updateBtnVerified(cdata['verified'])
        except AttributeError as e:
            print('error loading image: ', e)

    def toggleShowTab(self, show):
        t = self.gui.tabs
        t.setTabEnabled(t.indexOf(self), show)

    def buildTree(self, tree):
        show = bool(tree)
        if show:
            self.list.show()
            citem = self.list.currentItem()
            
            root = self.list.invisibleRootItem()
            last = [root, None, None]

            def _addParam(name, params, nindents):
                if nindents:
                    parent = last[nindents - 1]
                else:
                    parent = root
                item = self.list.findChildItem(parent, name)
                if item is None:
                    item = QtWidgets.QTreeWidgetItem(parent, [name])
                    if params:
                        if nindents == 2:
                            # modifiable:
                            item.setData(0, QtCore.Qt.UserRole,
                                         self._excludeUnchangableKeys(params))
                        else:
                            # nindents==1 -> grid
                            item.setData(0, QtCore.Qt.UserRole, params)

                        self._changeVerifiedColor(item)

                last[nindents] = item
                if params:
                    params = params
                    # original:
                    item.setData(1, QtCore.Qt.UserRole, params)

            # add new items / update existing:
            IDdict = {}
            for ID, data, meas in tree:
                _addParam(ID, data, 0)
                measdict = {}
                IDdict[ID] = measdict
#                 treenames.append([ID])
                for m, currents in meas:
                    _addParam(m, None, 1)
                    curlist = []
                    measdict[m] = curlist
                    for current, data in currents:
                        _addParam(current, data, 2)
                        curlist.append(current)

            # remove old ones:
            def iterremove(parent, dic):
                c = parent.childCount()
                i = 0
                while i < c:
                    child = parent.child(i)
                    txt = child.text(0)
                    if isinstance(dic, dict):
                        iterremove(child, dic[txt])
                        if not child.childCount():
                            # ... or empty parent items
                            parent.removeChild(child)
                            c -= 1
                            i -= 1
                    elif txt not in dic:
                        # only remove 'current' items
                        parent.removeChild(child)
                        c -= 1
                        i -= 1
                    i += 1

            iterremove(root, IDdict)
                    
            root.sortChildren(0, QtCore.Qt.AscendingOrder)
            self.list.resizeColumnToContents(0)
            if citem is None or citem.parent() is None:
                self.list.setCurrentItem(self.list.itemAt(0, 0))
        self.toggleShowTab(show)

    def modules(self):
        '''
        return generator for all module names in .list
        '''
        item = self.list.invisibleRootItem()
        for i in range(item.childCount()):
            yield item.child(i).text(0)

    def checkUpdates(self):
        if self.gui.server.isReady() and self.gui.server.hasNewCheckTree():
            self.buildTree(self.gui.server.checkTree())

    def _toggleVerified(self):
        item = self._getIDmeasCur()[2]
        data = item.data(0, QtCore.Qt.UserRole)
        v = data['verified'] = not data['verified']
        item.setData(0, QtCore.Qt.UserRole, data)

        self._updateBtnVerified(v)
        self._changeVerifiedColor(item)

    def _updateBtnVerified(self, verified):
        if verified:
            self.btn_markCurrentDone.setText('Mark unverified')
        else:
            self.btn_markCurrentDone.setText('Mark verified    ')

    def _changeVerifiedColor(self, item):
        data = item.data(0, QtCore.Qt.UserRole)
        if data is None or 'verified' not in data:
            return
        if data['verified']:
            color = QtCore.Qt.darkGreen
        else:
            color = QtCore.Qt.black
        item.setForeground(0, color)

        # apply upwards, if there is only one item in list
        while True:
            parent = item.parent()
            if not parent:
                break
            if parent.childCount() == 1:
                item = parent
                item.setForeground(0, color)
            else:
                break

    def _acceptAll(self):
        reply = QtWidgets.QMessageBox.question(
            self, 'Submitting changes', "Are you sure?",
            QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            self._doSubmitAllChanges()

    def _doSubmitAllChanges(self):
        out = {'grid': {}, 'unchanged': {}, 'changed': {}}
        for item, nindent in self.list.buildCheckTree():
            data = item.data(0, QtCore.Qt.UserRole)
            if nindent == 1:
                # only grid and curr interesting
                continue
            path = '\\'.join(self.list.itemInheranceText(item))
            changed = item.font(0).bold()
            print(path, data, nindent)
            if nindent == 2:
                if changed:  # item is modified
                    out['changed'][path] = data
                else:
                    out['unchanged'][path] = data['verified']
            elif changed:
                out['grid'][path] = data  # ['verified']
        self.gui.server.submitChanges(json.dumps(out) + '<EOF>')

#     def config(self):
#         return {}
#     def restoreState(self, c):
#         pass


if __name__ == '__main__':
    from fancytools.os.PathStr import PathStr
    from client.Application import Application

    app = Application()
    w = TabCheck()
    w.show()
    app.exec_()
