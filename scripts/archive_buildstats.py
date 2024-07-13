#!/usr/bin/env python3
#
# SPDX-License-Identifier: GPL-2.0-only
#
import glob, os, random, subprocess, socket, sys

def usage():
     print("Usage: " + sys.argv[0] + " <src> <dest> <target>")

def main():
    if len(sys.argv) != 4:
        usage()
        sys.exit()

    builddir = sys.argv[1]
    dest = sys.argv[2]
    target = sys.argv[3]
    dest_bsdir = os.path.join(dest, target, "buildstats")

    build_bsdir = os.path.join(builddir, "tmp/buildstats")
    if not os.path.exists(build_bsdir):
        sys.exit(0)

    subprocess.run(["mkdir", "-p", dest_bsdir])
    hostname = socket.gethostname()
    os.chdir(build_bsdir)
    fail_path = os.path.join(dest, target, "intermittent_failure_host_data")
    fail_output = glob.glob(fail_path + '/*top_summary.txt')

    #archive the buildstats of failures and 1% of random builds
    if fail_output or random.randint(1,100)%100 == 0:
        for timestamp in os.listdir(build_bsdir):
            if hostname:
                output = hostname + "-" + timestamp + ".tar.zst"
            else:
                output = "nohostname-"+ timestamp + ".tar.zst"
            subprocess.check_call("tar -I zstd -cf "+output+" "+timestamp+"/*", shell=True)
            subprocess.run(["mv", output, dest_bsdir])

main()
