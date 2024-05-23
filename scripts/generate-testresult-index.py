#!/usr/bin/env python3
#
# Copyright Linux Foundation, Richard Purdie
#
# SPDX-License-Identifier: GPL-2.0-only
#

import argparse
import os
import glob
import json
import re
import subprocess
from jinja2 import Template

def parse_args(argv=None):
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
            description="Generate an html index for a directory of autobuilder results",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('path', help='path to directory to index')

    return parser.parse_args(argv)

args = parse_args()
path = os.path.abspath(args.path)
entries = []
filter_items = dict()
build_types = set()
branch_list= set()

def get_build_branch(p):
    for root, dirs, files in os.walk(p):
        for name in files:
            if name == "testresults.json":
                f = os.path.join(root, name)
                with open(f, "r") as filedata:
                    data = json.load(filedata)
                for build in data:
                    try:
                        return data[build]['configuration']['LAYERS']['meta']['branch']
                    except KeyError:
                        continue 

    return ""

# Pad so 20190601-1 becomes 20190601-000001 and sorts correctly
def keygen(k):
    m = re.match(r"(\d+)-(\d+)", k)
    if m:
        k1, k2 = m.groups()
        return k1 + "-" + k2.rjust(6, '0')
    else:
        return k

for build in sorted(os.listdir(path), key=keygen, reverse=True):
    buildpath = os.path.join(path, build, "testresults")
    if not os.path.exists(buildpath):
        # No test results
        continue
    reldir = "./" + build + "/"

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

    testreport = ""
    if os.path.exists(buildpath + "/testresult-report.txt"):
        testreport = reldir + "testresults/testresult-report.txt"

    regressionreport = ""
    if os.path.exists(buildpath + "/testresult-regressions-report.txt"):
        regressionreport = reldir + "testresults/testresult-regressions-report.txt"

    ptestlogs = []
    ptestseen = []
    for p in glob.glob(buildpath + "/*-ptest/*.log"):
        if p.endswith("resulttool-done.log"):
            continue
        buildname = os.path.basename(os.path.dirname(p))
        if buildname not in ptestseen:
            ptestlogs.append((reldir + "testresults/" + buildname + "/", buildname.replace("-ptest","")))
            ptestseen.append(buildname)

    perfreports = []
    for p in glob.glob(buildpath + "/buildperf*/*.html"):
        perfname = os.path.basename(os.path.dirname(p))
        perfreports.append((reldir + "testresults/" + perfname + "/" + os.path.basename(p), perfname.replace("buildperf-","")))

    buildhistory = []
    if os.path.exists(buildpath + "/qemux86-64/buildhistory.txt"):
        buildhistory.append((reldir + "testresults/qemux86-64/buildhistory.txt", "qemux86-64"))

    if os.path.exists(buildpath + "/qemuarm/buildhistory.txt"):
        buildhistory.append((reldir + "testresults/qemuarm/buildhistory.txt", "qemuarm"))

    hd = []
    for p in glob.glob(buildpath + "/*/*/host_stats*summary.txt"):
        n_split = p.split(build)
        res = reldir[0:-1] + n_split[1]
        n = os.path.basename(p).split("host_stats_")[-1]
        if "failure" in n:
            n = n.split("_summary.txt")[0]
        elif "top" in n:
            n = n.split("_top_summary.txt")[0]
        hd.append((res, n))


    branch = get_build_branch(buildpath)

    build_types.add(btype)
    if branch: branch_list.add(branch)
    # Creates a dictionary of items to be filtered for build types and branch
    filter_items["build_types"] = build_types
    filter_items["branch_list"] = branch_list

    entry = {
        'build': build, 
        'btype': btype,
        'reldir': reldir 
    }

    if testreport:
        entry['testreport'] = testreport
    if branch:
        entry['branch'] = branch
    if buildhistory:
        entry['buildhistory'] = buildhistory
    if perfreports:
        entry['perfreports'] = perfreports
    if ptestlogs:
        entry['ptestlogs'] = ptestlogs
    if hd:
        entry['hd'] = hd
    if regressionreport:
        entry['regressionreport'] = regressionreport

    entries.append(entry)

    # Also ensure we have saved out log data for ptest runs to aid debugging
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

with open("./index-table.html") as file_:
    t = Template(file_.read())

with open(os.path.join(path, "data.json"), 'w') as f:
    json.dump(entries, f)

with open(os.path.join(path, "index.html"), 'w') as f:
    f.write(t.render(entries = entries, filter_items = filter_items))
