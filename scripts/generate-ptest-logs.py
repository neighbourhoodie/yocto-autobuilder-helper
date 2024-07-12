#!/usr/bin/env python3
#
# Copyright Linux Foundation, Richard Purdie
#
# SPDX-License-Identifier: GPL-2.0-only
#

import argparse
import os
import glob
import re
import time
import subprocess

def parse_args(argv=None):
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
            description="Generate separate ptest logs from any testresults.json files",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('path', help='path to directory to index')

    return parser.parse_args(argv)

args = parse_args()
path = os.path.abspath(args.path)

# Pad so 20190601-1 becomes 20190601-000001 and sorts correctly
def keygen(k):
    m = re.match(r"(\d+)-(\d+)", k)
    if m:
        k1, k2 = m.groups()
        return k1 + "-" + k2.rjust(6, '0')
    else:
        return k

current_time = time.time()

# number of seconds in 7 days
days = 7 * 24 * 60 * 60

for build in sorted(os.listdir(path), key=keygen, reverse=True):
    buildpath = os.path.join(path, build, "testresults")
    if not os.path.exists(buildpath):
        # No test results
        continue
    reldir = "./" + build + "/"
    modified_time = os.stat(buildpath).st_mtime

    # Only consider things in the last X days
    if (modified_time < (current_time - days)):
        continue

    btype = "other"
    files = os.listdir(buildpath)
    if os.path.exists(buildpath + "/a-full-posttrigger") or \
            os.path.exists(buildpath + "/a-full"):
        btype = "full"
    elif os.path.exists(buildpath + "/a-quick-posttrigger") or \
            os.path.exists(buildpath + "/a-quick"):
        btype = "quick"
    elif len(files) == 1:
        btype = files[0]

    # Ensure we have saved out log data for ptest runs to aid debugging
    if "ptest" in btype or btype in ["full", "quick"]:
        for root, dirs, files in os.walk(buildpath):
            for name in dirs:
                if "ptest" in name:
                    f = os.path.join(root, name)
                    logs = glob.glob(f + "/*.log")
                    if logs:
                        continue
                    subprocess.check_call(["resulttool", "log", f, "--dump-ptest", f])
                    # Ensure we don't rerun every time with a dummy log
                    with open(f + "/resulttool-done.log", "a+") as tf:
                        tf.write("\n")

