#!/usr/bin/env python3

import subprocess
import re
import json
import os, sys
from git import Repo
import semver
from collections import defaultdict
import datetime

GIT_REPO = '~/git/poky'

        

def get_git_tags():
    repo = Repo(GIT_REPO)
    tagmap = {}
    for t in repo.tags:
        tagmap.setdefault(repo.commit(t), []).append(t)

    def convert_name(tag):
        tags = tagmap[tag.commit]
        for t in tags:
            #print(t.commit,t.name)
            if 'yocto' not in t.name and '.rc' not in t.name:
                return ''.join(filter(str.isalpha, t.name)).capitalize()
        return 'BranchMissing'

    tags = list(filter(lambda e: 'yocto' in e.name, repo.tags))

    # Collect tag information into a list of dictionaries
    tag_list = []
    branches = sorted(set([tag.name[:9] for tag in tags]))
    #Remove bad tags
    branches.remove("yocto-1.9")
    branches.remove('yocto_1.5')
    branches.remove("yocto-1.4")

    old_branches = [] # removing old branches for now.
    #old_branches = ["inky-1.0", "clyde-2.0", "blinky-3.0", "pinky-3.1", "purple-3.2", "green-3.3", 
    #    "laverne-4.0", "bernard-5.0", "edison-6.0", "denzil-7.0", "danny-8.0", "dylan-9.0"]

    odd_commit_strings = ["rc", "final", "docs"]
    for branch in old_branches + branches:
        tags = list(filter(lambda e: branch in e.name and not any( x in e.name for x in odd_commit_strings), repo.tags))
        
        download = ""
        release_notes = ""
        if tags[-1].commit.committed_datetime >= repo.commit("73f103bf9b2cdf985464dc53bf4f1cfd71d4531f").committed_datetime:
            download = "https://downloads.yoctoproject.org/releases/yocto/{}".format(tags[-1].name)
            release_notes = "https://downloads.yoctoproject.org/releases/yocto/{}/RELEASENOTES".format(tags[-1].name)

        status  = "EOL"
        if branch == 'yocto-3.1':
            status = "LTS until Apr. 2024"
        if branch == 'yocto-4.0':
            status = "LTS until Apr. 2026"
        if branch == 'yocto-4.2':
            status = "Stable Release"

        # Create a dictionary for the tag
        tag_dict = {
            'series_version': re.sub(r"[^\d\.]", "", tags[0].name),
            'original_release_date': tags[0].commit.committed_datetime.isoformat(),
            'latest_release_date': tags[-1].commit.committed_datetime.isoformat(),
            'release_codename': convert_name(tags[0]),
            'latest_tag': re.sub(r"yocto-", "", tags[-1].name),
            'status': status,
            'download': download,
            'release_notes': release_notes
        }
        tag_list.append(tag_dict)
    
    return tag_list

# Usage
tags = sorted(get_git_tags(), key=lambda x: x['original_release_date'], reverse=False)
tags.append({
            'series_version': "4.3",
            'original_release_date': "",
            'latest_release_date': "",
            'release_codename': "Nanbield",
            'latest_tag': "",
            'status': "Active Development",
            'download': "",
        })
tags.append({
            'series_version': "5.0",
            'original_release_date': "",
            'latest_release_date': "",
            'release_codename': "Scarthgap",
            'latest_tag': "",
            'status': "Announced",
            'download': "",
        })

tags.reverse()

previous_release_series = 3
for tag in tags:
    if tag['status'] == 'EOL':
        if previous_release_series > 0:
            tag['series'] = 'previous';
            previous_release_series -= 1
        else:
            tag['series'] = 'full';
    else:
        tag['series'] = 'current';


with open('releases.json', 'w') as file:
    json.dump(tags, file)
