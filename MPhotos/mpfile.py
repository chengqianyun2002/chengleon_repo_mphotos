# -*- coding:gbk -*-
#!/usr/bin/env python
import os
import os.path
import time
import pyexiv2
import hashlib
import sys
reload(sys)
sys.setdefaultencoding('gbk')

class MPFile:
    def __init__(self, configs, logs, root, fullpath):
        self.configs = configs    # the configurations in xml doc
        self.logs = logs          # the logs instance to log message
        self.root = root          # the root path to run the script
        self.fullpath = fullpath  # the original fullpath of this file
        self.filename     = ""    # the original filename of this file
        self.new_fullpath = ""    # the new fullpath of this file after managing
        self.new_filename = ""    # the new filename of this file after managing
        self.type = ""            # the type is "photo" or "video"
        self.size = 0             # the size of this file in bytes
        self.mtime = ""           # the modify time of this file at format: "2016-09-16 11:01:16"
        self.ptime = ""           # the photo taken time of this file at format: "2016-09-16 11:01:16"
        self.ktime = ""           # the key time of this file which determines the final folder of this file
        self.md5 = ""             # the md5 value of this file
        self.comments = ""        # the UserComment in exif of photo, it's used to store md5
        self.duplicate = False    # whether this file is a duplicate of another file
        self.locked = False       # indicate whether the file should be locked
        self.moved = False        # indicate whether the file is moved to new path
        self.filename_score = 0   # represents the score of the filename

    # Check the string is md5 value?
    def __is_md5(self, str):
        if not str:
            return False
        elif len(str) != 32:
            return False
        else:
            return True

    # Return a string containing information of this file
    def __str__(self):
        # it's a duplicate file?
        duplicate = "not duplicate"
        if self.duplicate:
            duplicate = "duplicate"

        # it's an locked file?
        locked = "not locked"
        if self.locked:
            locked = "locked"

        # is new fullpath empty?
        new_fullpath = self.new_fullpath
        if not new_fullpath:
            new_fullpath = "null"

        # is md5 empty?
        md5 = self.md5
        if not md5:
            md5 = "null"

        # compose the string to return
        return self.fullpath + ":\n" + \
               "    " + new_fullpath + "\n" + \
               "    " + self.type + "\n" + \
               "    " + str(self.size) + " bytes" + "\n" + \
               "    " + self.ktime + "\n" + \
               "    " + locked + "\n" + \
               "    " + duplicate + "\n" + \
               "    " + md5 + "\n"

    # Calculate the md5 value of this file
    def __calc_file_md5(self):
        if os.path.isfile(self.fullpath):
            myhash = hashlib.md5()
            f = file(self.fullpath, 'rb')
            while True:
                b = f.read(8096)
                if not b:
                    break
                myhash.update(b)
            f.close()
            return str(myhash.hexdigest())
        else:
            return ""

    # Function to read the information from photo exif section
    def __read_photo_exif(self):
        if self.type == "photo":
            try:
                metadata = pyexiv2.ImageMetadata(self.fullpath)
                metadata.read()
                # read UserComment, because we use it to store md5
                if 'Exif.Photo.UserComment' in metadata.exif_keys:
                    UserComment = metadata['Exif.Photo.UserComment']
                    if UserComment:
                        self.comments = UserComment.human_value
                # read DateTimeOriginal, this is the photo taken time
                if 'Exif.Photo.DateTimeOriginal' in metadata.exif_keys:
                    DateTimeOriginal = metadata['Exif.Photo.DateTimeOriginal']
                    if DateTimeOriginal:
                        strlst = DateTimeOriginal.raw_value.split(" ")
                        self.ptime = strlst[0].replace(":", "-") + " " + strlst[1]
            except:
                pass

    # Function to write md5 as a string into photo exif section
    def __write_md5_into_photo_exif(self):
        if self.type == "photo":
            try:
                metadata = pyexiv2.ImageMetadata(self.fullpath)
                metadata.read()
                # write the md5 into UserComment of exif
                if self.__is_md5(self.md5):
                    metadata['Exif.Photo.UserComment'] = pyexiv2.ExifTag('Exif.Photo.UserComment', self.md5)
                    metadata.write()
            except:
                pass

    # Function check whether the file name meet "20170906_name" format
    def __meet_filename_format(self, filename):
        if len(filename) >= 9:
            date = filename[0:8]
            try:
                time.strptime(date, "%Y%m%d")
                if filename[8] == '-' or filename[8] == '~' or filename[8] == '_':
                    return True
            except Exception, e:
                self.logs.log("Exception in __meet_filename_format: " + filename + ", " + str(e))

        return False

    # Function to calculate score of current filename
    def __calculate_filename_score(self):
        score = 50
        for i in range(len(self.filename)):
            if self.filename[i] >= u"\u4e00" and self.filename[i] <= u"\u9fa6":
                score += 1
        if self.filename.count("副本."):
            score -= 3
            count = self.filename.count("副本")
            if count > 1:
                score -= (count - 1) * 3
        if self.filename.count("Copy."):
            score -= 1
            count = self.filename.count("Copy")
            if count > 1:
                score -= (count - 1)
        return score

    def better_than(self, file2):
        if self.filename_score > file2.filename_score:
            return True
        elif self.filename_score == file2.filename_score:
            if len(self.filename) < len(file2.filename):
                return True
            elif len(self.filename) == len(file2.filename):
                if self.filename < file2.filename:
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False

    def set_duplicate(self):
        self.duplicate = True
        # if file is set as duplicate, should update new_fullpath
        if self.type == "video":
            root_duplicated_video = os.path.join(os.path.join(self.root, "duplicated"), "videos")
            self.new_fullpath = os.path.join(root_duplicated_video, self.new_filename)
        else:
            root_duplicated_photo = os.path.join(os.path.join(self.root, "duplicated"), "photos")
            self.new_fullpath = os.path.join(root_duplicated_photo, self.new_filename)

    # Function to parse this file
    def parse(self, force_renew_md5 = False, check_video_md5 = False):
        # calculate file name
        self.filename = self.fullpath.split(os.sep)[-1]

        # calculate filename score
        self.filename_score = self.__calculate_filename_score()

        # set duplicate as false by default
        self.duplicate = False

        # calculate file size and mtime
        state = os.stat(self.fullpath)
        self.size = state.st_size
        self.mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(state.st_mtime))

        # calculate file type
        if self.configs.is_photo(self.filename):
            self.type = "photo"
        elif self.configs.is_video(self.filename):
            self.type = "video"
        else:
            self.type = "unrecognized"
            self.md5 = "unregcognized0000000000000000000"
            root_unrecognized = os.path.join(self.root, "unrecognized")
            self.ptime = self.mtime
            self.ktime = self.mtime
            self.new_filename = self.filename
            self.new_fullpath = os.path.join(root_unrecognized, self.filename)
            return (True, "Unrecognized file")

        # read ptime and comments from exif
        if self.type == "photo":
            self.__read_photo_exif()

        # determine the ktime
        # the ktime actually represents which folder the file will be put in
        # the order to get the ptime: time in filename > ptime > mtime
        # the time in filename has the highest prioirty, thus user has the chance to set time for any file
        if self.__meet_filename_format(self.filename):
            date = self.filename[0:4] + "-" + self.filename[4:6] + "-" + self.filename[6:8]
            if self.ptime != "":
                self.ktime = date + self.ptime[10:len(self.ptime)]
            elif self.mtime != "":
                self.ktime = date + self.mtime[10:len(self.mtime)]
            else:
                self.ktime = date + " 00:00:00"
        elif self.ptime != "":
            self.ktime = self.ptime
        else:
            self.ktime = self.mtime

        # calculate the new_filename
        # ktime decides the prefix of the file and the store folder of the file
        if self.__meet_filename_format(self.filename):
            self.new_filename = self.filename
        else:
            self.new_filename = self.ktime.replace("-", "")[0:8] + "_" + self.filename

        # check whether the file should be locked?
        locktime = self.configs.get_lock_time()
        if locktime and self.ktime <= locktime:
            self.locked = True
            self.md5 = "locked00000000000000000000000000"
            return (True, "No error")

        # get md5 for the file
        if self.type == "photo":
            if self.__is_md5(self.comments) and not force_renew_md5:
                self.md5 = self.comments
            else:
                self.md5 = self.__calc_file_md5()
                if self.__is_md5(self.md5):
                    self.__write_md5_into_photo_exif()
        elif self.type == "video":
            if check_video_md5:
                self.md5 = self.__calc_file_md5()
            else:
                # use file size plus 0 as faked md5, e.g. 14289349000000000000000000000000
                self.md5 = str(self.size) + '0' * (32 - len(str(self.size)))

        # calculate new_fullpath
        if self.locked:
            self.new_fullpath = self.fullpath
        elif self.type == "unrecognized":
            root_unrecognized = os.path.join(self.root, "unrecognized")
            self.new_fullpath = os.path.join(root_unrecognized, self.filename)
        elif self.duplicate:
            if self.type == "video":
                root_duplicated_video = os.path.join(os.path.join(self.root, "duplicated"), "videos")
                self.new_fullpath = os.path.join(root_duplicated_video, self.new_filename)
            else:
                root_duplicated_photo = os.path.join(os.path.join(self.root, "duplicated"), "photos")
                self.new_fullpath = os.path.join(root_duplicated_photo, self.new_filename)
        elif self.type == "video":
            if self.new_filename[4:6] <= "03":
                root_year_video = os.path.join(os.path.join(self.root, self.new_filename[0:4]), "videos_s1")
                self.new_fullpath = os.path.join(root_year_video, self.new_filename)
            elif self.new_filename[4:6] <= "06":
                root_year_video = os.path.join(os.path.join(self.root, self.new_filename[0:4]), "videos_s2")
                self.new_fullpath = os.path.join(root_year_video, self.new_filename)
            elif self.new_filename[4:6] <= "09":
                root_year_video = os.path.join(os.path.join(self.root, self.new_filename[0:4]), "videos_s3")
                self.new_fullpath = os.path.join(root_year_video, self.new_filename)
            else:
                root_year_video = os.path.join(os.path.join(self.root, self.new_filename[0:4]), "videos_s4")
                self.new_fullpath = os.path.join(root_year_video, self.new_filename)
        elif self.type == "photo":
            customized_folder = self.configs.get_customized_folder_name(self.ktime)
            if customized_folder:
                root_year_customized = os.path.join(os.path.join(self.root, self.new_filename[0:4]), customized_folder)
                self.new_fullpath = os.path.join(root_year_customized, self.new_filename)
            else:
                root_year_month = os.path.join(os.path.join(self.root, self.new_filename[0:4]), self.new_filename[4:6])
                self.new_fullpath = os.path.join(root_year_month, self.new_filename)
        else:
            self.new_fullpath = self.fullpath

        # Return true if no error happend
        return (True, "No error")

    # Move file to the new fullpath
    def move_to_new_fullpath(self):
        if not self.locked and self.fullpath != self.new_fullpath and self.new_fullpath != "":
            len1 = len(self.new_fullpath)
            len2 = len(self.new_filename)
            if len1 > len2:
                try:
                    # Make folder if target folder doesn't exist
                    folder = os.path.dirname(self.new_fullpath)
                    if not os.path.exists(folder):
                        os.makedirs(folder)

                    # If there is file with same name in target folder, we have to change a name
                    temp = self.new_fullpath
                    for i in range(10000):
                        if not os.path.exists(temp):
                            self.new_fullpath = temp
                            break
                        else:
                            temp = self.new_fullpath
                            temp = temp[0 : temp.rfind(".")] + "_" + str(i + 2) + "." + temp[temp.rfind(".") + 1 :]

                    # Rename the file to the target folder
                    os.rename(self.fullpath, self.new_fullpath)
                except BaseException, e:
                    return (False, "Exception: " + str(e))

                # Return success if no exception is thrown
                self.moved = True
                return (True, "File " + self.fullpath + " was moved to " + self.new_fullpath)
            else:
                return (False, "The new fullpath is invalid: " + self.new_fullpath)
        else:
            return (True, 'No need to move file: ' + self.fullpath)
