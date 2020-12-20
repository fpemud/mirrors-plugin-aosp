#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import re
import sys
import json
import time
import glob
import shutil
import certifi
import subprocess
import lxml.html
import urllib.request
import mirrors.plugin


def main():
    with mirrors.plugin.ApiClient() as sock:
        runMode = json.loads(sys.argv[1])["run-mode"]
        dataDir = json.loads(sys.argv[1])["storage-file"]["data-directory"]

        if runMode == "init":
            _init(dataDir, sock)
        elif runMode == "update":
            _update(dataDir, sock)
        else:
            assert False


def _init(dataDir, sock):
    extractCompeleteFile = os.path.join(dataDir, "extract.commplete")
    dstFile = None
    dstMd5File = None

    # find downloaded tar data file
    if True:
        tlist = glob.glob(os.path.join(dataDir, "*.tar"))
        tlist = [x for x in tlist if os.path.exists(x + ".md5")]
        if len(tlist) > 0:
            dstFile = tlist[-1]
            dstMd5File = dstFile + ".md5"
            _Util.deleteDirContent(dataDir, [dstFile, dstMd5File])
        else:
            _Util.deleteDirContent(dataDir)

    # continue
    if dstFile is not None:
        print("Verify \"%s\"." % (dstFile))
        ret = __verifyFile(dataDir, dstMd5File)
        if not ret:
            print("Get remote file list.")
            fnList = __getFileList()            # list<filename,url>

            dstFileUrl = None
            for fn, url in fnList:
                if os.path.basename(dstFile) == fn:
                    dstFileUrl = url
                    break

            if dstFileUrl is not None:
                print("Continue download \"%s\"." % (dstFileUrl))
                _Util.wgetContinueDownload(dstFileUrl, dstFile)
            else:
                dstFile = os.path.join(dataDir, fnList[-1][0])
                dstMd5File = dstFile + ".md5"
                _Util.deleteDirContent(dataDir)

                dstFileUrl = fnList[-1][1]
                dstMd5FileUrl = dstFileUrl + ".md5"
                print("Download \"%s\"." % (dstMd5FileUrl))
                _Util.wgetDownload(dstMd5FileUrl, dstMd5File)
                print("Download \"%s\"." % (dstFileUrl))
                _Util.wgetDownload(dstFileUrl, dstFile)

            print("Verify \"%s\"." % (dstFile))
            if not __verifyFile(dataDir, dstMd5File):
                raise Exception("the downloaded file is corrupt")
        else:
            pass
    else:
        print("Get remote file list.")
        fnList = __getFileList()            # list<filename,url>

        dstFile = os.path.join(dataDir, fnList[-1][0])
        dstMd5File = dstFile + ".md5"

        dstFileUrl = fnList[-1][1]
        dstMd5FileUrl = dstFileUrl + ".md5"
        print("Download \"%s\"." % (dstMd5FileUrl))
        _Util.wgetDownload(dstMd5FileUrl, dstMd5File)
        print("Download \"%s\"." % (dstFileUrl))
        _Util.wgetDownload(dstFileUrl, dstFile)

        print("Verify \"%s\"." % (dstFile))
        if not __verifyFile(dataDir, dstMd5File):
            raise Exception("the downloaded file is corrupt")

    # progress
    sock.progress_changed(50)

    # extract
    if not os.path.exists(extractCompeleteFile):
        print("Extract \"%s\"." % (dstFile))
        _Util.deleteDirContent(dataDir, [dstFile, dstMd5File])
        _Util.shellCallIgnoreResult("/bin/tar -x --strip-components=1 -C \"%s\" -f \"%s\"" % (dataDir, dstFile))
        with open(extractCompeleteFile, "w") as f:
            f.write("")

    # progress
    sock.progress_changed(60)

    # sync
    print("Synchonize.")
    with _TempChdir(dataDir):
        _Util.cmdExec("/usr/bin/repo", "sync")

    # progress
    sock.progress_changed(99)

    # all done, delete tar data file, md5 file, extract complete flag file
    print("Clean up.")
    _Util.forceDelete(dstFile)
    _Util.forceDelete(dstMd5File)
    _Util.forceDelete(extractCompeleteFile)

    # progress
    sock.progress_changed(100)


def _update(dataDir, sock):
    with _TempChdir(dataDir):
        _Util.cmdExec("/usr/bin/repo", "sync")


def __getFileList():
    url = "https://mirrors.tuna.tsinghua.edu.cn/aosp-monthly"
    ret = []

    resp = urllib.request.urlopen(url, timeout=60, cafile=certifi.where())
    root = lxml.html.parse(resp)
    for trElem in root.xpath(".//table[@id='list']/tbody/tr"):
        aTag = trElem.xpath("./td")[0].xpath("./a")[0]
        m = re.fullmatch("aosp-[0-9]+\\.tar", aTag.text)
        if m is not None:
            ret.append((m.group(0), os.path.join(url, aTag.get("href"))))
    if len(ret) == 0:
        raise Exception("no tar data file found")

    ret.sort(key=lambda x: x[0])
    return ret


def __verifyFile(dataDir, md5Filename):
    with _TempChdir(dataDir):
        return _Util.cmdCallTestSuccess("/usr/bin/md5sum", "-c", md5Filename)


class _Util:

    @staticmethod
    def deleteDirContent(path, fullfnIgnoreList=[]):
        for fn in os.listdir(path):
            fullfn = os.path.join(path, fn)
            if fullfn in fullfnIgnoreList:
                continue
            _Util.forceDelete(fullfn)

    @staticmethod
    def wgetDownload(url, localFile=None):
        param = _Util.wgetCommonDownloadParam().split()
        if localFile is None:
            _Util.cmdExec("/usr/bin/wget", *param, url)
        else:
            _Util.cmdExec("/usr/bin/wget", *param, "-O", localFile, url)

    @staticmethod
    def wgetContinueDownload(url, localFile=None):
        param = _Util.wgetCommonDownloadParam().split()
        if localFile is None:
            _Util.cmdExec("/usr/bin/wget", "-c", *param, url)
        else:
            _Util.cmdExec("/usr/bin/wget", "-c", *param, "-O", localFile, url)

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
    def cmdCallTestSuccess(cmd, *kargs):
        ret = subprocess.run([cmd] + list(kargs),
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             universal_newlines=True)
        if ret.returncode > 128:
            time.sleep(1.0)
        return (ret.returncode == 0)

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
