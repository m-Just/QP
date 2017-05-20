# -*- coding: utf-8 -*-
import sys, socket, Queue

from thread_manager import NetworkThread, ThreadManager

REMOTE_SERVER = "cusis.cuhk.edu.hk"

def is_connected():
    try:
        host = socket.gethostbyname(REMOTE_SERVER)
        s = socket.create_connection((host, 80), 2)
        return True
    except:
        pass
    return False
    
def attempt_connect(thread):
    elapsed = 0
    while not is_connected():
        print "Network unavailable..."
        thread.sleep(1)
        elapsed += 1
        if elapsed >= 3:
            print "Failed to connect to CUSIS, please check your Internet connection"
            return False
        print "Retry for connection..."
    return True
    
def check_connection():
    # Network check
    return_queue = Queue.Queue()
    network_thread = NetworkThread(return_queue, attempt_connect)
    manager = ThreadManager(1, (network_thread,), (return_queue,))
    manager.start()     # Thread would block here until CUSIS can be connected
    
    return manager.get()[0]