#!/usr/bin/env python3

import json
import subprocess
import sys

builddir = sys.argv[1]

jsonprops = {}
jsonprops['yp_build_revision'] =  subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=builddir).decode('utf-8').strip()
jsonprops['yp_build_branch'] = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=builddir).decode('utf-8').strip()

print(json.dumps(jsonprops, indent=4, sort_keys=True))


