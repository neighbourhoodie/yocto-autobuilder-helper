#! /usr/bin/env python3

import argparse
import collections
import dataclasses
import logging
import pickle
import pprint
import re

import arrow
import bugzilla
import requests


http = requests.Session()


def buildbot(server, method, **args):
    r = http.get(server + "/api/v2/" + method, params=args)
    r.raise_for_status()
    return r.json()


@dataclasses.dataclass
class Bug:
    id: int
    summary: str
    created: arrow.Arrow
    seen: list[arrow.Arrow] = dataclasses.field(default_factory=list)

    @property
    def count(self):
        return len(self.seen)

    @property
    def latest(self):
        try:
            return max(self.seen)
        except ValueError:
            return self.created

    @property
    def since(self):
        return arrow.now() - self.latest

    @property
    def weekly(self):
        c = collections.Counter()
        for started_at in self.seen:
            week = started_at.floor("week")
            c[week] += 1
        return dict(c)


def get_data():
    url_re = r"(?P<server>https?://autobuilder.yoctoproject.org/typhoon/)#/?builders/(?P<builder>\d+)/builds/(?P<build>\d+)"

    logging.debug("Searching bugzilla for AB-INT bugs...")
    bz = bugzilla.Bugzilla("https://bugzilla.yoctoproject.org/rest")
    # add limit=5 for speed
    query = bz.build_query(
        status_whiteboard="AB-INT",
        status_whiteboard_type="substring",
        include_fields=("id", "summary", "creation_time"),
    )
    # Weird
    query["resolution"] = "---"
    bugs = bz.query(query)
    bugs = [
        Bug(id=bug.id, summary=bug.summary, created=arrow.get(bug.creation_time))
        for bug in bugs
    ]

    pprint.pprint(bugs)
    print(f"Found {len(bugs)} AB-INT bugs")

    comments_data = bz.get_comments([bug.id for bug in bugs])["bugs"]

    for bug in bugs:
        for comment in comments_data[str(bug.id)]["comments"]:
            for match in re.finditer(url_re, comment["text"]):
                server = match.group("server")
                builder = int(match.group("builder"))
                build = int(match.group("build"))

                try:
                    response = buildbot(server, f"builders/{builder}/builds/{build}")
                    started_at = arrow.get(response["builds"][0]["started_at"])
                    logging.debug(f"Found occurance on {started_at}")
                    bug.seen.append(started_at)
                except requests.exceptions.HTTPError as e:
                    logging.debug(f"Couldn't find build for {builder=} {build=}")

    return bugs



def last_seen_report(data):
    import jinja2

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader("."),
        autoescape=jinja2.select_autoescape(),
        extensions=["jinja2_humanize_extension.HumanizeExtension"],
    )

    template = env.get_template("abint.html.j2")
    with open("index.html", "w") as f:
        start = arrow.utcnow().shift(weeks=-100).floor("week")
        f.write(template.render(bugs=data, start=start, now=arrow.now()))


CACHE_NAME = "bugs.data"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--cached", action="store_true", help="Use the local cached data instead of fetching")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if args.cached:
        logging.debug(f"Loading cached data from {CACHE_NAME}")
        with open(CACHE_NAME, "rb") as f:
            data = pickle.load(f)
    else:
        data = get_data()
        # Always save a cache because it's quick
        logging.debug(f"Saving data to cache {CACHE_NAME}")
        with open(CACHE_NAME, "wb") as f:
            pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)

    last_seen_report(data)
