#!/usr/bin/env python3

import hashlib
import json
import os
import subprocess
import sys

import utils

# Usage: scripts/getproperties.py <builddir> [builder_name]
builddir = sys.argv[1]
targetname = sys.argv[2] if len(sys.argv) > 2 else None

with open(builddir + "/../layerinfo.json") as f:
    repos = json.load(f)

utils.filterrepojson(repos)

def get_revision(repopath):
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repopath).decode('utf-8').strip()

def get_branch(repopath):
   return subprocess.check_output(["git", "name-rev", "--name-only", "--exclude=refs/tags*", "HEAD"], cwd=repopath).decode('utf-8').strip()

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
    if not os.path.exists(layerpath) and repo in ['meta-security']:
        # Repos is specified on the controller but not used in the helper config
        continue
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

jsonprops['use_bitbake_setup'] = True

ourconfig = utils.loadconfig()
exported_properties = ['DISTRO', 'MACHINE', 'SDKMACHINE', 'PACKAGE_CLASSES']
if targetname in ourconfig['overrides']:
    target_props = {}
    target = ourconfig['overrides'][targetname]
    maxsteps = 1
    # For each properties, construct of set of all values this property is
    # assigned with.
    # We iterate each steps, and get corresponding values from:
    # - The step itself.
    # - If no value was found, the build target template.
    # - If still not value is found, the defaults value.
    for v in target:
        if v.startswith("step"):
            for prop in exported_properties:
                for propdict in (target[v], target, ourconfig['defaults']):
                    if prop in propdict:
                        target_props.setdefault(prop, set()).add(propdict[prop])
                        break

    # Transform property sets: as single value if the set only contains one
    # value, as a list of values otherwise.
    for k, v in target_props.items():
        jsonprops[k] = list(v)[0] if len(v) == 1 else list(v)

print(json.dumps(jsonprops, indent=4, sort_keys=True))
