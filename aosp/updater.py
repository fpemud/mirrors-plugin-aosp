#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import sys
import json
import time
import subprocess
import mirrors.plugin


def main():
    with mirrors.plugin.ApiClient():
        logDir = json.loads(sys.argv[1])["log-directory"]
        dataDir = json.loads(sys.argv[1])["storage-file"]["data-directory"]
        with _TempChdir(dataDir):
            _Util.shellCall("/usr/bin/repo sync >\"%s\" 2>&1" % (os.path.join(logDir, "repo.log")))


class _Util:

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
