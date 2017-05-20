# -*- coding: utf-8 -*-
import sys

from PyQt4 import QtGui, QtCore

def fatalNetworkError():
    msgBox = QtGui.QMessageBox(None)
    msgBox.setWindowTitle('CusisPlus - Error')
    msgBox.setText('Cannot connect to Internet, please check your network and try again later')
    msgBox.show()
    msgBox.exec_()
            
    print "Error: Failed to connect to Internet, program abort"
    sys.exit(1)