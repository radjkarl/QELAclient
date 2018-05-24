import json
from PyQt5 import QtWidgets, QtCore

from client.dialogs import LineEditPassword, LineEditMail
from client.widgets._Base import QMessageBox


class Account(QtWidgets.QWidget):

    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.setWindowTitle('Account')
        self.setWindowIcon(gui.windowIcon())

        info = self.gui.server.accountInfo()

        lay = QtWidgets.QGridLayout()

        lay.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(lay)
        
        lay.addWidget(QtWidgets.QLabel('<b>Current</b>'), 0, 1)
        lay.addWidget(QtWidgets.QLabel('<b>New</b>'), 0, 2)

        lay.addWidget(QtWidgets.QLabel('User name: '), 1, 0)
        lay.addWidget(QtWidgets.QLabel(self.gui.user), 1, 1)

        lay.addWidget(QtWidgets.QLabel('Mobile phone: '), 2, 0)
        print(info, 888888888)
        lay.addWidget(QtWidgets.QLabel('+%s' % info['mobile']), 2, 1)

        lay.addWidget(QtWidgets.QLabel('Password: '), 4, 0)
        p = self.gui.pwd
        if p:
            pwd = '*' * len(p)
        else:
            pwd = '*******'
        lay.addWidget(QtWidgets.QLabel(pwd), 4, 1)
        
        self.edPwd1 = LineEditPassword()
        self.edPwd1.textChanged.connect(self.checkInput)

        lay.addWidget(self.edPwd1, 4, 2)
        self.edPwd2 = LineEditPassword() 
        self.edPwd2.textChanged.connect(self.checkInput)
        lay.addWidget(QtWidgets.QLabel('Repeat:'), 5, 1)
        lay.addWidget(self.edPwd1, 5, 2)

        lay.addWidget(QtWidgets.QLabel('Email: '), 6, 0)
        lay.addWidget(QtWidgets.QLabel(info['email']), 6, 1)

        self.edMail = LineEditMail()
        lay.addWidget(self.edMail, 6, 2)
        self.edMail.textChanged.connect(self.checkInput)

        lay.addWidget(QtWidgets.QLabel('Notification settings'), 7, 0)
        opts = ("Don't message me", 'Keep me updated',)
        n = opts[info['notification']]
        self.labNotification = QtWidgets.QLabel(n)
        lay.addWidget(self.labNotification, 7, 1)

        self.cbNotification = QtWidgets.QComboBox()
        self.cbNotification.addItems(opts)
        self.cbNotification.setCurrentText(n)
        self.cbNotification.currentIndexChanged.connect(self.checkInput)
        lay.addWidget(self.cbNotification, 7, 2)

        lay.setRowMinimumHeight(8, 30)

        lay.addWidget(QtWidgets.QLabel('<b>PRO features</b>'), 9, 1, 1, 2)
        
        lay.addWidget(QtWidgets.QLabel('Credit data'), 10, 0)
        lay.addWidget(QtWidgets.QLabel('todo'), 10, 1)
        lay.addWidget(QtWidgets.QLabel('todo'), 10, 2)

        lay.addWidget(QtWidgets.QLabel('Subscription'), 11, 0)
        n = info['subscription']
        self.labSubscription = QtWidgets.QLabel(n)
        lay.addWidget(self.labSubscription, 11, 1)

        self.cbSubscription = QtWidgets.QComboBox()
        self.cbSubscription.addItems(('free', "pro", 'premium'))
        self.cbSubscription.setCurrentText(n)
        self.cbSubscription.currentIndexChanged.connect(self.checkInput)
        lay.addWidget(self.cbSubscription, 11, 2)

        self.btnUpdate = QtWidgets.QPushButton('Update settings')
        self.btnUpdate.clicked.connect(self._update)
        self.btnUpdate.setEnabled(False)
        lay.addWidget(self.btnUpdate, 12, 0, 1, 3)
        
        lay.setRowMinimumHeight(13, 30)
        
        btn = QtWidgets.QPushButton('Delete user')
        btn.clicked.connect(self._delete)
        lay.addWidget(btn, 14, 0, 1, 3)

    def checkInput(self):   
        valid = all([
            not self.edPwd1.text() or self.edPwd1.hasAcceptableInput(),
            self.edPwd1.text() == self.edPwd2.text(),
            not self.edMail.text() or self.edMail.hasAcceptableInput()
            ])
        
        changed = any([self.edPwd1.text(), self.edMail.text(),
            self._subscriptionChanged(),
            self._notificationChanged()])
        
        self.btnUpdate.setEnabled(valid and changed)

    def _subscriptionChanged(self):
        return self.cbSubscription.currentText() != self.labSubscription.text() 

    def _notificationChanged(self):
        return self.cbNotification.currentText() != self.labNotification.text()

    def _update(self):
        pwd, res = QtWidgets.QInputDialog.getText(self, 'Enter password',
                                             'Please enter your current password for verification.',
                                             QtWidgets.QLineEdit.Password)
        if res:
            d = {}
            if self.edMail.text():
                d['email'] = self.edMail.text()
            if self.edPwd1.text():
                d['password'] = self.edPwd1.text()
            if self._subscriptionChanged():
                d['subscription'] = self.cbSubscription.currentText()
            if self._notificationChanged():
                d['notification'] = self.cbNotification.currentIndex()            

            res = self.gui.server.accountInfoSet(pwd, json.dumps(d))
            
            if res != "OK":
                QtWidgets.QMessageBox.critical(self, 'Error changing account details', res)

    def _delete(self):
        box = QMessageBox(QtWidgets.QMessageBox.Warning, 'Removing account ...',
                                    '''You will not longer be able to use this software,<br>
but you can still access your data at <br>
<a href='file:{p}'>{p}</a> <br>
Are you sure to remove this account?'''.format(p=self.gui.PATH_USER),
                                        QtWidgets.QMessageBox.Yes | 
                                          QtWidgets.QMessageBox.No)
                                    
        box.setTextFormat(QtCore.Qt.RichText)
        res = box.exec_()

        if res == QtWidgets.QMessageBox.Yes:
            self.gui.server.deleteAccount()
            QtWidgets.QApplication.instance().quit()
