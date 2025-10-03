#!/usr/bin/env python3

import hashlib
import json
import os
import subprocess
import sys

import utils

builddir = sys.argv[1]


with open(builddir + "/../layerinfo.json") as f:
    repos = json.load(f)

utils.filterrepojson(repos)

def get_revision(repopath):
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repopath).decode('utf-8').strip()

def get_branch(repopath):
   return subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repopath).decode('utf-8').strip()

jsonprops = {}
jsonprops['commit_yocto-autobuilder-helper'] = get_revision(builddir + "/../yocto-autobuilder-helper/")
jsonprops['branch_yocto-autobuilder-helper'] = get_branch(builddir + "/../yocto-autobuilder-helper/")
#set below to a combined hash
#jsonprops['yp_build_revision'] = get_revision(builddir + "/layers/openembedded-core/")
jsonprops['yp_build_branch'] = get_branch(builddir + "/layers/openembedded-core/")

done = []

def getrevs(jsonprops, layerpath, layername):
    jsonprops['commit_' + layername] = get_revision(layerpath)
    jsonprops['branch_' + layername ] = get_branch(layerpath)

for layer in os.listdir(builddir + "/layers"):
    layerpath = builddir + "/layers/" + layer
    if layer == "logs" or os.path.islink(layerpath):
        continue
    if not os.path.isdir(layerpath):
        continue

    layername = layer
    if layer == "openembedded-core":
        layername = "oecore"
    getrevs(jsonprops, layerpath, layername)
    done.append(layername)

for repo in sorted(repos.keys()):
    if repo in done:
        continue
    layerpath = builddir + '/' + repo
    if not os.path.exists(layerpath):
        # layer may not be used by the build and hence not moved into final position
        layerpath = builddir + '/repos/' + repo
    #if not os.path.exists(layerpath):
    #    # Repos is specified on the controller but not used in the helper config
    #    continue
    getrevs(jsonprops, layerpath, repo)

# We need a way to match builds which are the same in the buildbot UI. Traditionally this was
# done with an poky revision.
# Compute a dummy sha1 of the combination of oecore, bitbake and the helper revisions
buildid = ""
for repo in ['oecore', 'bitbake', 'yocto-autobuilder-helper']:
    if 'commit_' + repo in jsonprops:
        buildid += jsonprops['commit_' + repo]
buildid = hashlib.sha1(buildid.encode("utf-8")).hexdigest()

jsonprops['yp_build_revision'] = buildid

print(json.dumps(jsonprops, indent=4, sort_keys=True))

