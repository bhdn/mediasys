import os
import subprocess
import logging
from mediasys import Error

logger = logging.getLogger("mediasys.rpmpackage")

class CommandError(Error):
    pass

class RPMPackageError(Error):
    pass

class RPMPackage:

    name = None
    epoch = None
    version = None
    release = None
    distepoch = None
    disttag = None
    arch = None
    group = None
    fullversion = None

    def __init__(self, path):
        self.path = path
        self._loadtags(path)

    def _loadtags(self, path):
        tags = ("name", "epoch", "version", "release", "distepoch",
                "disttag", "arch", "group")
        queryformat = "\\n".join("%%{%s}" % tag for tag in tags)
        out = self._rpmq(path, queryformat)
        fields = out.split("\n")
        if len(fields) < len(tags):
            raise RPMPackageError, "%s does not seem to be a RPM package" % (path)
            err = RPMPackageError("no lines from the RPM output: %s" % (out))
            raise err
        def g(it):
            val = it.next()
            if val == "(none)":
                return None
            return val
        it = iter(fields)
        self.name = g(it)
        self.epoch = g(it)
        self.version = g(it)
        self.release = g(it)
        self.distepoch = g(it)
        self.disttag = g(it)
        self.arch = g(it)
        self.group = g(it)
        #'1:2.1-63:2011.0'
        self.fullversion = "%s:%s-%s:%s" % (self.epoch or "0", self.version,
                self.release, self.distepoch or "(none)")

    def _rpmq(self, path, qf):
        args = ["/bin/rpm", "-q", "-p", "--qf"]
        args.append(qf)
        args.append(path)
        cmdline = subprocess.list2cmdline(args)
        logger.debug("running %s" % (cmdline))
        proc = subprocess.Popen(args=args, shell=False,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.wait()
        if proc.returncode != 0:
            errorout = proc.stderr.read()
            cmdline = subprocess.list2cmdline(args)
            raise CommandError, ("rpm failed with %d\n%s\n%s" %
                    (proc.returncode, cmdline, errorout))
        return proc.stdout.read()

    def filename(self):
        return os.path.basename(self.path)
