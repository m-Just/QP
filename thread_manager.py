# -*- coding: utf-8 -*-
import Queue

from PyQt4 import QtGui, QtCore

from selenium import webdriver

import config

# Handle event loops that wait on single or multiple thread(s)
class ThreadManager(QtCore.QObject):
    def __init__(self, thread_num, thread_list, queue_list):
        QtCore.QObject.__init__(self)
        self.thread_num = thread_num
        self.thread_list = thread_list
        self.queue_list = queue_list

        for thread in thread_list:
            thread.connect(thread, QtCore.SIGNAL('finished()'), self, QtCore.SLOT('thread_finished()'))

        self.threadFinished = 0
        self.singal_emitter = QtCore.QObject()

    def start(self):
        for thread in self.thread_list:
            thread.start()
        loop = QtCore.QEventLoop()
        loop.connect(self.singal_emitter, QtCore.SIGNAL('destroyed()'), loop, QtCore.SLOT('quit()'))
        loop.exec_()

    def get(self):
        data = list()
        for queue in self.queue_list:
            data.append(queue.get())
            queue.task_done()
        return data

    @QtCore.pyqtSlot()
    def thread_finished(self):
        self.threadFinished += 1
        if self.threadFinished == self.thread_num:
            del self.singal_emitter     # note: use keyword del to destroy an object, emitting signal destroyed()


class BrowserInitThread(QtCore.QThread):
    def __init__(self, queue, dest, func, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.queue = queue
        self.dest = dest
        self.func = func

    def run(self):
        if config.DRIVER_IN_USE == 'PhantomJS':
            driver = webdriver.PhantomJS()
            # Avoid race condition where the find element is executing before it is present on the page
            driver.implicitly_wait(config.DRIVER_IMPLICIT_WAIT)
            self.queue.put(self.func(driver, self.dest))
        elif config.DRIVER_IN_USE == 'Chrome':
            chromeOptions = webdriver.ChromeOptions()
            prefs = {"profile.managed_default_content_settings.images":2}   # Disable image rendering
            chromeOptions.add_experimental_option("prefs",prefs)
            driver = webdriver.Chrome(chrome_options=chromeOptions)
            self.queue.put(self.func(driver, self.dest))


class BrowserThread(QtCore.QThread):
    def __init__(self, queue, func, data, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.queue = queue
        self.func = func
        self.data = data

    def run(self):
        self.queue.put(self.func(self.data))
        #except:
        #    self.queue.put('Error')

class NetworkThread(QtCore.QThread):
    def __init__(self, queue, func, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.queue = queue
        self.func = func

    def run(self):
        self.queue.put(self.func(self))
