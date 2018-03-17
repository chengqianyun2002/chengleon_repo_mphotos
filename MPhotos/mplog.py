#!/usr/bin/env python
from datetime import datetime
import sys
reload(sys)
sys.setdefaultencoding('gbk')

class MPLog:
    def __init__(self, log_file):
        self.logfile = None
        try:
            self.logfile = open(log_file, "a")
            self.logfile.write(self.__time() + "======================================== MPhotos Starts ========================================")
            self.logfile.write("\n")
        except:
            pass

    def __del__(self):
        if self.logfile:
            self.logfile.write(self.__time() + "========================================= MPhotos Ends =========================================")
            self.logfile.write("\n")
            self.logfile.close()

    def __time(self):
        return datetime.today().isoformat(sep=' ')[0:23] + ": "

    def log(self, str):
        if self.logfile:
            self.logfile.write(self.__time() + str)
            self.logfile.write("\n")
