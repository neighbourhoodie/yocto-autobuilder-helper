#! /usr/bin/env python3

import re
import collections
from pprint import pprint
import bugzilla
import pickle
import requests
import dataclasses
import arrow
import logging

MOCK = False
# logging.basicConfig(level=logging.DEBUG)


def save_pickle(name, data):
    with open(name, "wb") as f:
        pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)


def load_pickle(name):
    with open(name, "rb") as f:
        return pickle.load(f)


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

    pprint(bugs)
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

    save_pickle("bugs.data", bugs)
    return bugs


if MOCK:

    def get_data():
        return load_pickle("bugs.data")


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


data = get_data()
last_seen_report(data)
