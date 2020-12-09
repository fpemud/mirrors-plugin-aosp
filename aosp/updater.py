#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import sys
import json
import time
import shutil
import hashlib
import subprocess
import mirrors.plugin


def main():
    with mirrors.plugin.ApiClient() as sock:
        runMode = json.loads(sys.argv[1])["run-mode"]
        dataDir = json.loads(sys.argv[1])["storage-file"]["data-directory"]

        if runMode == "init":
            dstFileUrl = "https://mirrors.tuna.tsinghua.edu.cn/aosp-monthly/aosp-latest.tar"
            dstFile = os.path.join(dataDir, "aosp-latest.tar")
            dstMd5FileUrl = dstFileUrl + ".md5"
            dstMd5File = dstFile + ".md5"

            # download md5 file
            print("Download \"aosp-latest.tar.md5\".")
            _Util.wgetDownload(dstMd5FileUrl, dstMd5File)
            sock.progress_changed(5)

            # download data file
            print("Download \"aosp-latest.tar\".")
            if not os.path.exists(dstFile) or not _Util.verifyFileMd5(dstFile, dstMd5File):
                _Util.wgetDownload(dstFileUrl, dstFile)
                if not _Util.verifyFileMd5(dstFile, dstMd5File):
                    raise Exception("the just downloaded file is corrupt")
            sock.progress_changed(50)

            # clear directory
            print("Clear cache directory.")
            for fn in os.listdir(dataDir):
                fullfn = os.path.join(dataDir, fn)
                if fullfn in [dstFile, dstMd5File]:
                    continue
                _Util.forceDelete(fullfn)
            sock.progress_changed(55)

            # extract
            # sometimes tar file contains minor errors
            print("Extract aosp-latest.tar.")
            _Util.shellCallIgnoreResult("/bin/tar -x --strip-components=1 -C \"%s\" -f \"%s\"" % (dataDir, dstFile))
            sock.progress_changed(60)

            # sync
            print("Synchonize.")
            with _TempChdir(dataDir):
                _Util.cmdExec("/usr/bin/repo", "sync")
            sock.progress_changed(99)

            # all done, delete the tar data file and md5 file
            _Util.forceDelete(dstFile)
            _Util.forceDelete(dstMd5File)
            sock.progress_changed(100)
        elif runMode == "update":
            # sync
            with _TempChdir(dataDir):
                _Util.cmdExec("/usr/bin/repo", "sync")
        else:
            assert False


class _Util:

    @staticmethod
    def verifyFileMd5(filename, md5sum):
        with open(filename, "rb") as f:
            thash = hashlib.md5()
            while True:
                block = f.read(65536)
                if len(block) == 0:
                    break
                thash.update(block)
            return thash.hexdigest() == md5sum

    @staticmethod
    def wgetDownload(url, localFile=None):
        param = _Util.wgetCommonDownloadParam().split()
        if localFile is None:
            _Util.cmdExec("/usr/bin/wget", *param, url)
        else:
            _Util.cmdExec("/usr/bin/wget", *param, "-O", localFile, url)

    @staticmethod
    def wgetCommonDownloadParam():
        return "-q --show-progress -t 0 -w 60 --random-wait -T 60 --passive-ftp"

    @staticmethod
    def forceDelete(filename):
        if os.path.islink(filename):
            os.remove(filename)
        elif os.path.isfile(filename):
            os.remove(filename)
        elif os.path.isdir(filename):
            shutil.rmtree(filename)

    @staticmethod
    def cmdExec(cmd, *kargs):
        # call command to execute frontend job
        #
        # scenario 1, process group receives SIGTERM, SIGINT and SIGHUP:
        #   * callee must auto-terminate, and cause no side-effect
        #   * caller must be terminate AFTER child-process, and do neccessary finalization
        #   * termination information should be printed by callee, not caller
        # scenario 2, caller receives SIGTERM, SIGINT, SIGHUP:
        #   * caller should terminate callee, wait callee to stop, do neccessary finalization, print termination information, and be terminated by signal
        #   * callee does not need to treat this scenario specially
        # scenario 3, callee receives SIGTERM, SIGINT, SIGHUP:
        #   * caller detects child-process failure and do appopriate treatment
        #   * callee should print termination information

        # FIXME, the above condition is not met, _Util.shellExec has the same problem

        ret = subprocess.run([cmd] + list(kargs), universal_newlines=True)
        if ret.returncode > 128:
            time.sleep(1.0)
        ret.check_returncode()

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
