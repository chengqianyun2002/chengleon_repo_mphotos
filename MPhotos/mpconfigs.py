#!/usr/bin/env python
import xml.etree.cElementTree as ET
import sys
reload(sys)
sys.setdefaultencoding('gbk')

class MPConfigs:
    def __init__(self, config_file):
        self.__tree = ET.ElementTree(file=config_file)
        self.__root = self.__tree.getroot()
        for child in self.__root:
            if child.tag == "lock-time":
                self.__lock_time = child
            elif child.tag == "photo-formats":
                value = child.attrib["value"].strip().lower().replace(' ', '')
                self.__photo_formats = value.split(',')
            elif child.tag == "video-formats":
                value = child.attrib["value"].strip().lower().replace(' ', '')
                self.__video_formats = value.split(',')
            elif child.tag == "special-photos":
                value = child.attrib["value"].strip().replace(' ', '')
                self.__special_photos = value.split(',')
            elif child.tag == "special-videos":
                value = child.attrib["value"].strip().replace(' ', '')
                self.__special_videos = value.split(',')
            elif child.tag == "customized-photo-folders":
                self.__customized_photo_folders = child

    def __del__(self):
        #self.__tree.write('mphotos.xml')
        pass

    # Get the time string of lock date in format: "2016-09-16 11:01:16"
    def get_lock_time(self):
        return self.__lock_time.attrib["value"]

    # Check whether the file is a photo file
    def is_photo(self, filename):
        suffix = filename.split('.')[-1].lower()
        if self.__photo_formats.count(suffix) > 0:
            return True
        elif self.__special_photos.count(filename) > 0:
            return True
        else:
            return False

    # Check whether the file is a video file
    def is_video(self, filename):
        suffix = filename.split('.')[-1].lower()
        if self.__video_formats.count(suffix) > 0:
            return True
        elif self.__special_videos.count(filename) > 0:
            return True
        else:
            return False

    # Get the specified folder name by timer string, e.g. "2016-09-16 11:01:16"
    def get_customized_folder_name(self, timestr):
        for child in self.__customized_photo_folders:
            if timestr >= child.attrib["from"] and timestr <= child.attrib["to"]:
                return child.attrib["name"]
        return None
