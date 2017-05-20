# -*- coding: utf-8 -*-
import sys, re, json, string, os.path, Queue, time
from datetime import datetime

from PyQt4 import QtGui, QtCore

import selenium
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

import network_manager, data_manager
from planner import CourseInfo
from browser import Browser
from thread_manager import ThreadManager, BrowserInitThread, BrowserThread

TERM_CODE = {
    0: '1945',  # Term 1
    1: '1955',  # Term 2
    2: '1990',  # Summer Session
    3: '1940',  # Academic Year (Medicine)
}

TERM_NAME = {
    0: 'Term 1',
    1: 'Term 2',
    2: 'Summer',
    3: 'Year',
}

class LoginWindow(QtGui.QWidget):
    ERRORS = {
        'NETWORK_ERROR': 'Cannot connect to CUSIS. Check your Internet connection.',
        'CREDENTIAL_ERROR': 'Student ID or Password is invalid.',
        'NOT_RESTARTABLE_ERROR': 'Fatal error ocurred. Please close the program and try again later.',
    }

    def __init__(self, browser1, browser2, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.browser1 = browser1
        self.browser2 = browser2

        self.setWindowTitle('CusisPlus-Login')
        self.setFixedSize(400, 400)
        #self.resize(400, 300) #this is resizable

        #self.setToolTip('This is the login window')

        self.initUI()

    def keyPressEvent(self, qKeyEvent):
        if qKeyEvent.key() == QtCore.Qt.Key_Return:
            self.submit.click()


    def initUI(self):
        # TODO
        # add a update checker




        titleLabel = QtGui.QLabel('Student ID', parent=self)
        passwdLabel = QtGui.QLabel('Password', parent=self)
        msgLabel = QtGui.QLabel(parent=self)
        msgLabel.setText('Welcome to CusisPlus!')
        msgLabel.setWordWrap(True)

        titleEdit = QtGui.QLineEdit(parent=self)
        titleEdit.connect(titleEdit, QtCore.SIGNAL('textEdited(QString)'),   # QString stores the new text and will be passed to the connected SLOT, if not specified the SIGNAL won't work
            msgLabel, QtCore.SLOT("clear()"))
        passwdEdit = QtGui.QLineEdit(parent=self)
        passwdEdit.setEchoMode(QtGui.QLineEdit.Password)
        passwdEdit.connect(passwdEdit, QtCore.SIGNAL('textEdited(QString)'),
            msgLabel, QtCore.SLOT("clear()"))

        titleEdit.setMaxLength(10)
        passwdEdit.setMaxLength(20)

        termLabel = QtGui.QLabel('Term', parent=self)

        termSelect = QtGui.QComboBox(self)
        termSelect.addItem('Term 1')
        termSelect.addItem('Term 2')
        termSelect.addItem('Summer Session')
        termSelect.addItem('Acad Year (Medicine)')

        month = datetime.now().month
        if month > 10 or month < 2:
            termSelect.setCurrentIndex(1)
        elif month < 6:
            termSelect.setCurrentIndex(2)
        else:
            termSelect.setCurrentIndex(0)

        submitButton = QtGui.QPushButton('Login', parent=self)
        submitButton.clicked.connect(lambda: self.login(submitButton, termSelect.currentIndex()))

        self.username = titleEdit
        self.password = passwdEdit
        self.message = msgLabel
        self.submit = submitButton

        grid = QtGui.QGridLayout()    # grid layout
        grid.setSpacing(30)
        grid.setMargin(50)

        grid.addWidget(titleLabel, 1, 0, 1, 1)
        grid.addWidget(passwdLabel, 2, 0, 1, 1)

        grid.addWidget(titleEdit, 1, 1, 1, 1)
        grid.addWidget(passwdEdit, 2, 1, 1, 1)

        grid.addWidget(termLabel, 3, 0, 1, 1)
        grid.addWidget(termSelect, 3, 1, 1, 1)

        grid.addWidget(msgLabel, 4, 0, 3, 2)

        grid.addWidget(submitButton, 7, 1, 1, 1)

        self.setLayout(grid)


    def browserLogin(self, username, password, term_code, term_name):
        token = {'username': username, 'password': password, 'term_code': term_code, 'term_name': term_name}

        queue1 = Queue.Queue()
        queue2 = Queue.Queue()
        thread1 = BrowserThread(queue1, self.browser1.login, token)
        thread2 = BrowserThread(queue2, self.browser2.login, token)

        manager = ThreadManager(2, (thread1, thread2), (queue1, queue2))
        manager.start()
        status = manager.get()

        if status[0] == 1 and status[1] == 1:
            print "Browser login successful"
            return 0
        else:
            return 1

    def login(self, button, term_index):
        button.setText("Please wait")
        button.setEnabled(False)

        username = self.username.text()
        password = self.password.text()

        # Test network connection
        if not network_manager.is_connected():
            self.message.setStyleSheet("QLabel { color : red; }")
            self.message.setText(self.ERRORS['NETWORK_ERROR'])
            button.setText("Login")
            button.setEnabled(True)
            return
        else:
            self.message.setStyleSheet("QLabel { color : black; }")
            self.message.setText('Connected to CUSIS, logging in...')
            # Attempt login
            if not re.match('1155[0-9]{6}', self.username.text()) or not re.match('.{8,21}', self.password.text())\
            or self.browserLogin(username, password, TERM_CODE[term_index], TERM_NAME[term_index]):
                self.message.setStyleSheet("QLabel { color : red; }")
                self.message.setText(self.ERRORS['CREDENTIAL_ERROR'])
                button.setText("Login")
                button.setEnabled(True)
                return
            # Login success, loading schedule and initializing window
            else:
                self.message.setStyleSheet("QLabel { color : black; }")
                self.message.setText('Login success, loading data from CUSIS... This may take some time.')
                self.message.repaint()

                try:
                    # TODO
                    # catelogue reload depends on timestamp



                    data_manager.dataCrawl(str(self.username.text()), str(self.password.text()), TERM_NAME[term_index])
                except:
                    self.message.setStyleSheet("QLabel { color : red; }")
                    self.message.setText(self.ERRORS['NOT_RESTARTABLE_ERROR'])
                    print "Error: Data crawling fatal error."

        self.info = CourseInfo(self.browser1, self.browser2, TERM_NAME[term_index])
        self.info.show()
        self.close()

if __name__ == "__main__":
    print "Program started"

    app = QtGui.QApplication(sys.argv)

    pixmap = QtGui.QPixmap('./img/patience.png')
    programInitSplash = QtGui.QSplashScreen(pixmap)
    programInitSplash.show()

    queue1 = Queue.Queue()
    queue2 = Queue.Queue()
    thread1 = BrowserInitThread(queue1, 'CLASS_SEARCH', Browser)
    thread2 = BrowserInitThread(queue2, 'TEACHING_TABLE', Browser)

    manager = ThreadManager(2, (thread1, thread2), (queue1, queue2))
    manager.start()

    browser1, browser2 = manager.get()

    print "Browsers ready"

    login = LoginWindow(browser1, browser2)
    login.show()

    programInitSplash.finish(login)

    app.exec_()
    browser1.exit()
    browser2.exit()
    sys.exit(0)
