# -*- coding: utf-8 -*-
import logging

# Global errors
NETWORK_ERROR = -1

# Driver settings
DRIVER_OPTION = ('Chrome', 'PhantomJS')
DRIVER_IN_USE = DRIVER_OPTION[1]

DRIVER_IMPLICIT_WAIT = 0    # sec
DRIVER_EXPLICIT_WAIT = 10

# Logger
selenium_logger = logging.getLogger('selenium.webdriver.remote.remote_connection')
# Only display possible problems
selenium_logger.setLevel(logging.WARNING)
