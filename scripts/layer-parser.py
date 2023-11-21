#!/usr/bin/env python3

import os
import time
import requests
import json

LAYER_API_URL = "https://layers.openembedded.org/layerindex/api/layers/?filter=yp_compatible_version__isnull:false&format=json"
LAYERDATA = "layerdata.json"
RELEASE_URL = "https://docs.yoctoproject.org/releases.json"
RELEASEDATA = "releasedata.json"


def fetch_data(url, file_path, cache):
    if os.path.isfile(file_path):
        modification_time = os.path.getmtime(file_path)
        time_difference = time.time() - modification_time
    else:
        time_difference = 1000000

    # Re-download if the time difference is greater than cache value
    if time_difference > cache:
        response = requests.get(url)
        if response.status_code == 200:
            with open(file_path, "w") as file:
                file.write(response.text)
            return json.loads(response.text)
    else:
        with open(file_path, "r") as file:
            return json.load(file)


layers = fetch_data(LAYER_API_URL, LAYERDATA, 600)
releases = fetch_data(RELEASE_URL, RELEASEDATA, 600)

# grab the recent release branches and add master, so we can ignore old branches
active_releases = [
    e["release_codename"].lower() for e in releases if e["series"] != "full"
]
active_releases.append("master")
active_releases.append("main")

header = dict()
header["layer"] = "Layer"
header["branches"] = "Branches"
header["desc"] = "Description"
header["maintainers"] = ["Maintainer(s)"]
header["url"] = "Source Code"
parsed_layers = {"header": header}

for layer in layers:
    name = layer["layer"]["name"]
    if layer["branch"]["name"] not in active_releases:
        continue
    if name in parsed_layers:
        parsed_layers[name]["branches"] += ", " + layer["branch"]["name"]
        output["maintainers"].union(set([e["name"] for e in layer["maintainers"]]))
    else:
        output = dict()
        output["layer"] = name
        output["branches"] = layer["branch"]["name"]
        if len(layer["layer"]["description"]) > 80:
            output["desc"] = layer["layer"]["summary"]
        else:
            output["desc"] = layer["layer"]["description"]
        output["maintainers"] = set([e["name"] for e in layer["maintainers"]])
        output["url"] = '<a href="{u}">{u}</a>'.format(u=layer["layer"]["vcs_web_url"])
        parsed_layers[name] = output

# Convert the lists of maintainers to a pretty string
for layer in parsed_layers:
    maintainers = list(parsed_layers[layer]["maintainers"])
    if len(maintainers) == 1:
        parsed_layers[layer]["maintainers"] = maintainers.pop()
    else:
        print(maintainers)
        parsed_layers[layer]["maintainers"] = "{} and {}".format(
            ", ".join(maintainers[:-1]), maintainers[-1]
        )

with open("parsed-layers.json", "w") as file:
    json.dump(parsed_layers, file)
