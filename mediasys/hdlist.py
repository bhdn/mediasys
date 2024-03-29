import sys
import os
import gzip
import logging

logger = logging.getLogger("mediasys.hdlist")

class TypeSynthesis: pass
class TypeHdlist: pass

class Package:
    
    def __init__(self):
        self.name = None
        self.provides = None
        self.requires = None
        self.summary = None
        self.disttag = None
        self.distepoch = None
        self.fullname = None
        self.fullversion = None

    def __hash__(self):
        return hash(self.fullname)

    def __cmp__(self, other):
        if isinstance(other, Package):
            return cmp(self.fullname, other.fullname)
        else:
            return cmp(self.fullname, other)

    def __repr__(self):
        return "<%s>" % (self.fullname)

    def filename(self):
        return self.fullname + ".rpm"

class HdlistParser:

    def __init__(self, basedir, config, has_distepoch=False):
        self.path = os.path.join(basedir, config.metadata_dirname,
                config.synthesis_name)
        self.basedir = basedir
        self.compressed = False
        self._parsed = {}
        self._file = None
        self._done = False
        self._lines = None
        self.timestamp = None
        self.has_distepoch = has_distepoch
        self.guess_type()
        self.get_info()

    def get_info(self):
        stat = os.stat(self.path)
        self._size = stat.st_size
        self.timestamp = stat.st_mtime

    def guess_type(self):
        name = os.path.basename(self.path)
        if name.startswith("synthesis."):
            self.type = TypeSynthesis
        if name.endswith(".cz"):
            self.compressed = True

    def get(self, name):
        try:
            return self._parsed[name]
        except KeyError:
            while True:
                pkg = self.next()
                if not pkg:
                    break
                if pkg.name in self._parsed:
                    raise "opa:", pkg.name
                self._parsed[pkg.name] = pkg
                if pkg.name == name:
                    return pkg

    def next(self):
        if self._file is None:
            if self.compressed:
                #self._file = gzip.GzipFile(self.path, "r")
                _, self._file = os.popen2(["zcat", self.path], "r")
            else:
                self._file = open(self.path)
            logger.debug("loading %s", self.path)
            # python's gzip implementation is too slow
            data = self._file.read()
            logger.debug("readed %d bytes", len(data))
            self._lines = iter(data.splitlines())
        stop = False
        info = {}
        for line in self._lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("@info@"):
                # pkg done
                stop = True
            fields = line.split("@")
            name = fields[1]
            args = fields[2:]
            info[name] = args
            if stop:
                break
        else:
            self._done = True
            if not info:
                return
        #if self.compressed:
        #    readed = self._file.myfileobj.tell()
        #else:
        #    readed = self._file.tell()
        #self._progress = (100.0 / self._size) * readed
        verinfo = info["info"]
        namever = verinfo[0]
        pkg = Package()
        if len(verinfo) > 5:
            if namever.endswith(".src"):
                # source packages don't have the %disttag%distepoch suffix
                archinfo = namever
                namever = namever[:-len(".src")]
            else:
                namever, archinfo = namever.rsplit("-", 1)
            pkg.disttag = verinfo[4]
            pkg.distepoch = verinfo[5]
        else:
            archinfo = namever
        pkg.arch = archinfo.rsplit(".", 1)[1]
        nvr = namever.rsplit("-", 2)
        pkg.name = nvr[0]
        pkg.vr = "-".join(nvr[1:])
        pkg.epoch = verinfo[1]
        pkg.summary = info["summary"][0]
        pkg.provides = info.get("provides", [])
        pkg.requires = info.get("requires", [])
        pkg.fullversion = pkg.epoch + ":" + pkg.vr 
        pkg.fullname = verinfo[0]
        # stoopid:
        pkg.path = os.path.join(self.basedir, pkg.fullname + ".rpm")
        if len(verinfo) > 5:
            pkg.fullversion += ":" + pkg.distepoch
        return pkg

    def progress(self):
        return self._progress

class MediaInfo:

    hdlist = None
    name = None
    rpms = None
    noauto = False
    xmlinfo = None
    size = None
