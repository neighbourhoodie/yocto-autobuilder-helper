#! /usr/bin/env python3
#
# SPDX-License-Identifier: GPL-2.0-only
#
# This script will list all of the connected workers on the autobuilder.

import requests

buildbot_api = "https://autobuilder.yoctoproject.org/valkyrie/api/v2/"

http = requests.Session()

def buildbot(method, **args):
    return http.get(buildbot_api + method, params=args).json()

for worker in buildbot(f"workers")["workers"]:
    # Skip workers that are not connected to any controllers
    if not worker["connected_to"]:
        continue
    print(f"{worker['name']}.yocto.io")
