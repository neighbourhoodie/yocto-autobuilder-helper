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

index_template = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Index of autobuilder test results</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@0.9.1/css/bulma.min.css">
</head>
<body>
 
<table class="table is-narrow is-striped">
<thead>
<tr>
  <th>Build</th>
  <th>Type</th>
  <th>Branch</th>
  <th>Test Results Report</th>
  <th>Performance Reports</th>
  <th>ptest Logs</th>
  <th>Buildhistory</th>
  <th>Host Data</th>
</tr>
</thead>
<tdata>
{% for entry in entries %}
<tr>
   <td><a href="{{entry[1]}}">{{entry[0]}}</a></td>
   <td>{% if entry[2] %} {{entry[2]}}{% endif %}</td>
   <td>{% if entry[4] %} {{entry[4]}}{% endif %}</td>
   <td>
     {% if entry[3] %}<a href="{{entry[3]}}">Report</a>{% endif -%}
     {% if entry[9] %}<br><a href="{{entry[9]}}">Regressions</a>{% endif %}
   </td>
   <td>
   {% for perfrep in entry[6] %}
     <a href="{{perfrep[0]}}">{{perfrep[1]}}</a>
   {% endfor %}
   </td>
   <td>
   {% for ptest in entry[7] %}
     <a href="{{ptest[0]}}">{{ptest[1]}}</a>
   {% endfor %}
   </td>
   <td>
   {% for bh in entry[5] %}
     <a href="{{bh[0]}}">{{bh[1]}}</a>
   {% endfor %}
   </td>
   <td>
   {% for hd in entry[8] %}
     <a href="{{hd[0]}}">{{hd[1]}}</a>
   {% endfor %}
   </td>
</tr>
{% endfor %}
</tdata>
</table>
</body>
</html>
"""

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

    entries.append((build, reldir, btype, testreport, branch, buildhistory, perfreports, ptestlogs, hd, regressionreport))

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

t = Template(index_template)
with open(os.path.join(path, "index.html"), 'w') as f:
    f.write(t.render(entries = entries))
