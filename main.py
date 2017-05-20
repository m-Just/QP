# -*- coding: utf-8 -*-
import sys, Queue

from PyQt4 import QtGui, QtCore

from thread_manager import ThreadManager, BrowserInitThread
from login import LoginWindow
from browser import Browser

import network_manager, status

__author__ = "Kaican Li"
__copyright__ = None
__credits__ = ["Kaican Li"]
__license__ = None
__version__ = "0.0.2"
__maintainer__ = "Kaican Li"
__email__ = "mjust.lkc@gmail.com"
__status__ = "Production"

def init_network_check():
    retry = 0
    while not network_manager.is_connected():
        retry += 1
        if retry >= 3:
            status.fatalNetworkError()
            
if __name__ == "__main__":
    print "Program started"
    
    app = QtGui.QApplication(sys.argv)
    
    init_network_check()
    
    pixmap = QtGui.QPixmap('./img/patience.png')
    programInitSplash = QtGui.QSplashScreen(pixmap)
    programInitSplash.show()
    
    queue1 = Queue.Queue()
    queue2 = Queue.Queue()
    thread1 = BrowserInitThread(queue1, 'CLASS_SEARCH', Browser)
    thread2 = BrowserInitThread(queue2, 'TEACHING_TABLE', Browser)
    
    manager = ThreadManager(2, (thread1, thread2), (queue1, queue2))
    
    try:
        manager.start()
    except:
        init_network_check()
        print "Error: Failed to initialize browsers, program abort"
        sys.exit(0)
    
    browser1, browser2 = manager.get()
    
    print "Browsers ready"
    
    try:
        loginWin = LoginWindow(browser1, browser2)
        loginWin.show()
    except:
        print "Error: Failed to initialize login window, program abort"
        browser1.exit()
        browser2.exit()
        sys.exit(0)
    
    programInitSplash.finish(loginWin)
        
    app.exec_()
    
    browser1.exit()
    browser2.exit()
        
    sys.exit(0)