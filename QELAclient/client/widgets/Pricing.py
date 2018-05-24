# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets, QtCore, QtGui

# TODO: embedd payment in gui - no need for writing mails


def _fillTable(table, data):
    for x, row in enumerate(data):
        for y, cell in enumerate(row):
            item = QtWidgets.QTableWidgetItem()
            item.setText(cell)
            item.setFlags(QtCore.Qt.NoItemFlags | QtCore.Qt.ItemIsEnabled)
#             if cell == '-':
#                 item.setBackground(QtGui.QColor(255, 0, 0, 50))
#             elif cell == 'free':  # ✓':
#                 item.setBackground(QtGui.QColor(0, 255, 0, 50))
            table.setItem(x, y, item)
    font = table.horizontalHeader().font()
    font.setBold(True)
    table.horizontalHeader().setFont(font)

    font = table.verticalHeader().font()
    font.setBold(True)
    table.verticalHeader().setFont(font)
    table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)


def _green(table, x, y):
    table.item(x, y).setBackground(QtGui.QColor(0, 255, 0, 50))


class Pricing(QtWidgets.QWidget):

    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.setWindowTitle('Pricing')
        self.setWindowIcon(gui.windowIcon())

        self.resize(500, 365)

        lay = QtWidgets.QVBoxLayout()
        lay.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(lay)
  
        lab = QtWidgets.QLabel(
            "For an overview of recent transactions, please refer our invoice send monthly to your email address.<br>\
Charges are either <a href='monthly'>monthly</a> or per <a href='measurement'>measurement</a>.<br>\
To top-up credit balance, please <a href='contact'>contact</a> us.\
<br>An academic discount of 20% can be offered.")
        lab.linkActivated.connect(self._linkClicked)
        lab.linkHovered.connect(self._linkHovered)

        tableMem = QtWidgets.QTableWidget(2, 3)
        tableMem.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        tableMem.setHorizontalHeaderLabels(['free', '10 S$ / Month', '50 S$ / Month'])
        tableMem.setVerticalHeaderLabels(['Server storage           ', 'Daily allowance'])

        tableMem.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignLeft)
        tableMem.horizontalHeader().setStretchLastSection(True)

        _fillTable(tableMem, [['5 GB', '50 GB', '500 GB'],
                              ['100 Images', '500 Images', '1000 Images']])
        _green(tableMem, 0, 0)
        _green(tableMem, 1, 0)

        tableMem.setFixedHeight(60)
        tableMem.resizeRowsToContents()
        tableMem.setColumnWidth(0, 100)
        tableMem.verticalHeader().setFixedWidth(150)

        table = QtWidgets.QTableWidget(8, 2)
#         table.verticalHeader().hide()
        table.horizontalHeader().hide()
        table.setColumnWidth(0, 100)

        data = [['Camera calibration\n', ''],
                ['Image correction\n', ''],
                ['', 'Image quality and uncertainty\n'],
                ['', 'Image enhancement\n'],
                ['', 'Post processing\n(Cell averages, Cracks etc.)'],
                ['', 'Performance analysis\n(Power + Energy loss)'],
                ['', 'One PDF report for every measurement\n'],
                ['', 'One PDF report for every used camera\n']
                ]
        _fillTable(table, data)
        _green(table, 0, 0)
        _green(table, 1, 0)

        table.setVerticalHeaderLabels(['', '', 'pro (1 S$ / Measurement)', '', '', '', '', ''])

        table.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignLeft)
        table.horizontalHeader().setStretchLastSection(True)
        
        table.verticalHeader().setFixedWidth(150)
        
        table.setFixedHeight(250)
        table.resizeRowsToContents()

        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        lay.addWidget(lab)
        lay.addWidget(tableMem)
        lay.addWidget(table)
#         lay.addWidget(QtWidgets.QLabel(
#             '<b>  Everything:              1S$ / Image</b>'))
        lay.addStretch()
        
        self.setFocus()  # remove focus from a specific cell

    def _linkHovered(self, txt):
        tip = None
        if txt == 'measurement':
            tip = '''A measurement is defined as the result of one or multiple electroluminescence images,
taken during ONE continuous process at ONE fixed current'''
        elif txt == 'monthly':
            tip = '''One month is defined as the duration of 30 days from beginning 
of using the service.'''
        if tip:
            QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), tip)
        else:
            QtWidgets.QToolTip.hideText()

    def _linkClicked(self, txt):
        if txt == 'contact':
            self.gui.menuShowContact()


if __name__ == '__main__':
    from client.widgets.Contact import Contact
    from client.Application import Application
    
    app = Application()

    class DummyGui:

        def menuShowContact(self):
            DummyGui.contact = Contact()
            DummyGui.contact.show()

        def windowIcon(self):
            return QtGui.QIcon()

    w = Pricing(DummyGui())

    w.show()
    app.exec_()
