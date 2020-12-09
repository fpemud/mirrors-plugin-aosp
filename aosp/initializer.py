#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import sys
import json
import time
import shutil
import subprocess
import mirrors.plugin


def main():
    with mirrors.plugin.ApiClient() as sock:
        dataDir = json.loads(sys.argv[1])["storage-file"]["data-directory"]
        dstFile = os.path.join(dataDir, "aosp-latest.tar")
        usedFile = dstFile + ".used"

        if not os.path.exists(usedFile):
            # download
            print("Download \"aosp-latest.tar\".")
            if True:
                url = "https://mirrors.tuna.tsinghua.edu.cn/aosp-monthly/aosp-latest.tar"
                logFile = os.path.join(dataDir, "wget.log")
                _Util.shellCall("/usr/bin/wget -c -O \"%s\" \"%s\" >\"%s\" 2>&1" % (dstFile, url, logFile))
            sock.progress_changed(50)

            # clear directory
            print("Clear cache directory.")
            for fn in os.listdir(dataDir):
                fullfn = os.path.join(dataDir, fn)
                if fullfn != dstFile:
                    _Util.forceDelete(fullfn)
            sock.progress_changed(55)

            # extract
            # sometimes tar file contains minor errors
            print("Extract aosp-latest.tar.")
            _Util.shellCallIgnoreResult("/bin/tar -x --strip-components=1 -C \"%s\" -f \"%s\"" % (dataDir, dstFile))
            os.rename(dstFile, usedFile)
            sock.progress_changed(60)
        else:
            print("Found \"aosp-latest.tar.used\".")
            sock.progress_changed(60)

        # sync
        print("Synchonization starts.")
        with _TempChdir(dataDir):
            logFile = os.path.join(dataDir, "repo.log")
            _Util.shellCall("/usr/bin/repo sync >\"%s\" 2>&1" % (logFile))
        print("Synchonization over.")
        sock.progress_changed(99)

        # all done, delete the tar file
        _Util.forceDelete(usedFile)
        sock.progress_changed(100)


class _Util:

    @staticmethod
    def forceDelete(filename):
        if os.path.islink(filename):
            os.remove(filename)
        elif os.path.isfile(filename):
            os.remove(filename)
        elif os.path.isdir(filename):
            shutil.rmtree(filename)

    @staticmethod
    def shellCall(cmd):
        # call command with shell to execute backstage job
        # scenarios are the same as FmUtil.cmdCall

        ret = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             shell=True, universal_newlines=True)
        if ret.returncode > 128:
            # for scenario 1, caller's signal handler has the oppotunity to get executed during sleep
            time.sleep(1.0)
        if ret.returncode != 0:
            ret.check_returncode()
        return ret.stdout.rstrip()

    @staticmethod
    def shellCallIgnoreResult(cmd):
        ret = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             shell=True, universal_newlines=True)
        if ret.returncode > 128:
            time.sleep(1.0)


class _TempChdir:

    def __init__(self, dirname):
        self.olddir = os.getcwd()
        os.chdir(dirname)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        os.chdir(self.olddir)


###############################################################################

if __name__ == "__main__":
    main()
