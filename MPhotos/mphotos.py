#!/usr/bin/env python
import os
import os.path
import sys
import time
import mpconfigs
import mpfile
import mplog
from optparse import OptionParser
import sys
reload(sys)
sys.setdefaultencoding('gbk')

class MPhotos:
    # Constructor function
    def __init__(self):
        # get user input as command
        self.command = ""
        for i in range(len(sys.argv)):
            self.command += (sys.argv[i] + " ")
        self.command.strip()

        # get the install path of mphotos.py
        self.install_dir = os.path.dirname(sys.argv[0])

        # for progress output control
        self.last_progress_len = 0

        # get options from input command
        usage = "usage: %prog [options]"
        parser = OptionParser(usage=usage)
        parser.add_option("--path", action="store", dest="path", help="required, folder to files require management, managed files saved in --path")
        parser.add_option("--from", action="store", dest="from", help="optional, folder to files require management, managed files saved in --path")
        parser.add_option("--copy", action="store_true", dest="copy", default=False, help="optional, force to copy files from --from to --path")
        parser.add_option("--renew-photo-md5", action="store_true", dest="renew_photo_md5", default=False, help="optional, force to renew md5 for photo files")
        parser.add_option("--check-video-md5", action="store_true", dest="check_video_md5", default=False, help="optional, force to check md5 for video files")
        parser.add_option("--log-file", action="store", dest="log_file", help="optional, full path to specify the log file for this executing")
        (self.options, self.args) = parser.parse_args()

        # create the log class for logging
        if not self.options.log_file or self.options.log_file == "":
            log_file = "C:\\Users\\a\\mphotos.log"
        self.logs = mplog.MPLog(log_file)
        self.logs.log("Start with input command: " + self.command)

        # get configurations from configuration file
        config_file = os.path.join(self.install_dir, 'mphotos.xml')
        self.configs = mpconfigs.MPConfigs(config_file)

        # dict or list to contain different type files
        self.all_files = []
        self.valid_files = {}
        self.locked_files = []
        self.duplicated_files = []
        self.unrecognized_files = []

    # Function to validate input from user
    def __validate_input(self):
        # Check --path
        if not self.options.path:
            sys.stdout.write('Missing parameter --path\n')
            self.logs.log('Missing parameter --path\n')
            sys.stdout.write("Type \"mphotos --help\" for help\n")
            return False
        elif not os.path.exists(self.options.path):
            sys.stdout.write('The path does not exist: ' + self.options.path + '\n')
            self.logs.log('The path does not exist: ' + self.options.path + '\n')
            sys.stdout.write("Type \"mphotos --help\" for help\n")
            return False

        # Return true if everything is ok
        return True

    # Function to look up files in rootdir
    def __lookup_photos(self, rootdir):
        # Start progress display
        self.__show_progress("Lookup files", "start", 0)

        # lookup files
        for parent, dirnames, filenames in os.walk(rootdir):
            for filename in filenames:
                parent = parent.decode()
                filename = filename.decode()
                mpf = mpfile.MPFile(self.configs, self.logs, self.options.path, os.path.join(parent, filename))
                self.all_files.append(mpf)
                self.__show_progress("Lookup files", "middle", len(self.all_files), mpf.fullpath)

        # Complete progress display
        self.__show_progress("Lookup files", "end", len(self.all_files))
        self.logs.log("Found " + str(len(self.all_files)) + " files")

    # Function to analyze photos/videos in all_files[]
    def __analyze_photos(self):
        # Start progress display
        index = 0
        self.__show_progress("Analyze files", "start", index)

        for mpf in self.all_files:
            index += 1
            self.__show_progress("Analyze files", "middle", index, mpf.fullpath)

            # parse the file
            (result, error) = mpf.parse(self.options.renew_photo_md5, self.options.check_video_md5)

            # catalog the file
            if result:
                if mpf.locked:
                    self.locked_files.append(mpf)
                else:
                    if mpf.type == "unrecognized":
                        self.unrecognized_files.append(mpf)
                    else:
                        if self.valid_files.has_key(mpf.md5):
                            tmp = self.valid_files[mpf.md5]
                            if mpf.better_than(tmp):
                                # mpf better than tmp
                                tmp.set_duplicate()
                                self.duplicated_files.append(tmp)
                                self.valid_files[mpf.md5] = mpf
                            else:
                                # tmp better than mpf
                                mpf.set_duplicate()
                                self.duplicated_files.append(mpf)
                        else:
                            # mpf is unique
                            self.valid_files[mpf.md5] = mpf
            else:
                self.logs.log("Failed to parse file " + mpf.fullpath + ", error: " + error)

        # Complete progress display
        self.__show_progress("Analyze files", "end", index)
        self.logs.log("Analyzed " + str(index) + " files")

    # Function to process the analyzed photos/videos
    def __process_photos(self):
        # Start progress display
        index = len(self.locked_files)
        self.__show_progress("Process files", "start", index)

        # Process valid files
        for (key, mpf) in self.valid_files.items():
            index += 1
            self.__show_progress("Process files", "middle", index, mpf.fullpath)
            (result, msg) = mpf.move_to_new_fullpath()
            if not result:
                self.logs.log("Error: Failed to move file: " + msg)

        # Process duplicated files
        for mpf in self.duplicated_files:
            index += 1
            self.__show_progress("Process files", "middle", index, mpf.fullpath)
            (result, msg) = mpf.move_to_new_fullpath()
            if not result:
                self.logs.log("Error: Failed to move file: " + msg)

        # Process unrecognized files
        for mpf in self.unrecognized_files:
            index += 1
            self.__show_progress("Process files", "middle", index, mpf.fullpath)
            (result, msg) = mpf.move_to_new_fullpath()
            if not result:
                self.logs.log("Error: Failed to move file: " + msg)

        # Start progress display
        self.__show_progress("Process files", "end", index)
        self.logs.log("Processed " + str(index) + " files")

    # Function to remove empty directories
    def __remove_empty_directories(self, rootdir):
        if os.path.isdir(rootdir):
            for d in os.listdir(rootdir):
                self.__remove_empty_directories(os.path.join(rootdir,d))
            if not os.listdir(rootdir):
                try:
                    os.rmdir(rootdir)
                except Exception, e:
                    self.logs.log("Failed to remove " + str(rootdir) + ", error: " + str(e))

    # Function to show progress bar
    def __show_progress(self, step, substep, index = 0, file = ""):
        # clean last display
        if self.last_progress_len > 0:
            sys.stdout.write('\b' * self.last_progress_len + ' ' * self.last_progress_len)
            sys.stdout.flush()
            self.last_progress_len = 0

        # make display
        if step == "Lookup files":
            if substep == "start":
                sys.stdout.write("Looking up files now:\n")
                sys.stdout.flush()
                self.last_progress_len = 0
            elif substep == "middle":
                progress = "    " + str(index) + ":  " + file
                sys.stdout.write("\r" + progress)
                sys.stdout.flush()
                self.last_progress_len = len(progress)
            elif substep == "end":
                result = "\r    Done, " + str(index) + " files found\n"
                sys.stdout.write(result)
                sys.stdout.flush()
                self.last_progress_len = 0
        elif step == "Analyze files":
            if substep == "start":
                sys.stdout.write("Analyzing files now:\n")
                sys.stdout.flush()
                self.last_progress_len = 0
            elif substep == "middle":
                progress = "\r    " + str(index) + ":  " + file
                sys.stdout.write(progress)
                sys.stdout.flush()
                self.last_progress_len = len(progress)
            elif substep == "end":
                result = "\r    Done, " + str(index) + " files analyzed\n"
                sys.stdout.write(result)
                sys.stdout.flush()
                self.last_progress_len = 0
        elif step == "Process files":
            if substep == "start":
                sys.stdout.write("Processing files now:\n")
                sys.stdout.flush()
                self.last_progress_len = 0
            elif substep == "middle":
                progress = "\r    " + str(index) + ":  " + file
                sys.stdout.write(progress)
                sys.stdout.flush()
                self.last_progress_len = len(progress)
            elif substep == "end":
                result = "\r    Done, " + str(index) + " files processed\n"
                sys.stdout.write(result)
                sys.stdout.flush()
                self.last_progress_len = 0

    # Function to show statistic info
    def __show_statistic(self):
        print "Executing Done:"
        print "    The lock date           : " + self.configs.get_lock_time()
        print "    Total files             : " + str(len(self.all_files))
        print "    Total files valid       : " + str(len(self.valid_files))
        print "    Total files locked      : " + str(len(self.locked_files))
        print "    Total files duplicated  : " + str(len(self.duplicated_files))
        print "    Total files unrecognized: " + str(len(self.unrecognized_files))

    # function to compare 2 mpfiles
    def __compare(self, mpfile1, mpfile2):
        if mpfile1.md5 > mpfile2.md5:
            return 1
        elif mpfile1.md5 == mpfile2.md5:
            return 0
        else:
            return -1

    # Function to print sorted all files in log file
    def __log_sorted_all_files(self):
        self.all_files.sort(cmp = self.__compare)
        for mpf in self.all_files:
            tag = ""
            if mpf.locked:
                tag = "lockd"
            elif mpf.type == "unrecognized":
                tag = "unrec"
            elif mpf.duplicate:
                tag = "dupct"
            else:
                tag = "valid"

            info = mpf.md5 + " " + mpf.ktime + " " + tag + " " + str(mpf.filename_score) + " " + mpf.new_fullpath
            self.logs.log(info)

    # Main Function
    def main(self):
        #self.options.path = "c:\\test"
        if self.__validate_input():
            self.__lookup_photos(self.options.path)
            self.__analyze_photos()
            self.__process_photos()
            self.__remove_empty_directories(self.options.path)
            self.__show_statistic()
            self.__log_sorted_all_files()

def main():
    mphotos = MPhotos()
    mphotos.main()

if __name__ == "__main__":
    main()
