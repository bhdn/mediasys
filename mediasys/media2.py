import os
import fcntl
import time
import logging
from mediasys import Error
from mediasys import util, cmd
from mediasys.config import Config
from mediasys.rpmpackage import RPMPackage

class MediaError(Error):
    pass

class MediaLocked(MediaError):
    pass

class MetadataNotFound(MediaError):
    pass

logger = logging.getLogger("mediasys.media2")

class MediaInfo(object):

    def __init__(self, name):
        self.name = name
        self.tags = set()
        self.values = {}
        self._medias = set() # archname: Media

    def value(self, attrname, default=None):
        return self.values.get(attrname, default)

    def set_tag(self, name):
        self.tags.add(name)

    def set_value(self, name, value):
        self.values[name] = value

    def add_real_media(self, media):
        self._medias.add(media)

    def packages_by_source(self, sourcename):
        for media in self._medias:
            for found in media.packages_by_source(sourcename):
                yield found

from mediasys.hdlist import HdlistParser
from mediasys.infoxml import InfoxmlParser

class PackageSetError(Error):
    pass

class PackageSet(object):

    def __init__(self, packages=(), source=None):
        self._packages = set(packages)
        self._source = source

    def packages(self):
        return self._packages

    def remove_package(self, pkg):
        self.packages.remove(pkg)

    def source(self):
        return self._source

    @classmethod
    def from_filenames(self, filenames):
        """Returns a PackageSet from a file path sequence"""
        source = None
        binaries = set()
        for filename in filenames:
            pkg = RPMPackage(filename)
            if filename.endswith(".src.rpm"):
                if source is not None:
                    raise PackageSetError("currently mediasys doesn't allow "
                            "uploading more than one package set (ie. one "
                            "source package and its binaries")
                source = pkg
            else:
                binaries.add(pkg)
        if not source or not binaries:
            raise PackageSetError("at least one binary and one source "
                    "package should be provided")
        return PackageSet(binaries, source)

class URPMIMedia(object):

    def __init__(self, path, config):
        self.path = path
        self.config = config
        self.hdlist = None
        self.infoxml = None
        self.pkgs = None
        self.pkgs_by_fullname = None
        self.pkginfo = None
        self.srpms = None
        self.srpms_by_name = None
        self.lockfile = None
        logger.debug("created media at %s", path)

    def _load_synthesis(self):
        pkgs = set()
        byname = {}
        next = self.hdlist.next
        add = pkgs.add
        setdef = byname.setdefault
        while True:
            pkg = next()
            if pkg is None:
                break
            add(pkg)
            setdef(pkg.fullname, []).append(pkg)
        self.pkgs = pkgs
        self.pkgs_by_fullname = byname

    def _load_infoxml(self):
        self.pkginfo = self.infoxml.load()
        srpms = {}
        srpms_by_name = {}
        for info in self.pkginfo:
            srpm = info.get("sourcerpm")
            if srpm:
                srpms.setdefault(srpm, []).append(info)
                if "distepoch" in info or "disttag" in info:
                    name, versionrel, disttagarch = srpm.rsplit("-", 2)
                else:
                    name, version, rel = srpm.rsplit("-", 2)
                srpms_by_name.setdefault(name, []).append(info)
        self.srpms = srpms
        self.srpms_by_name  = srpms_by_name

    def load(self):
        try:
            self.hdlist = HdlistParser(self.path, self.config)
            self.infoxml = InfoxmlParser(self.path, self.config)
        except (IOError, EnvironmentError), e:
            raise MetadataNotFound("failed to load media metadta: "
                    "%s" % (e))
        self._load_synthesis()
        self._load_infoxml()

    def _lock_file(self):
        return os.path.join(self.path, self.config.metadata_dirname,
                self.config.lock_filename)

    def lock(self):
        path = self._lock_file()
        try:
            f = open(path, "a")
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(str(os.getpid()))
            f.flush()
            self.lockfile = f
        except EnvironmentError, e:
            raise MediaError("failed to write pid to lock file %s: %s" %
                    (path, e))

    def unlock(self):
        path = self._lock_file()
        if self.lockfile is None:
            raise MediaError("never locked")
        try:
            fcntl.flock(self.lockfile.fileno(), fcntl.LOCK_UN)
            self.lockfile.close()
            os.unlink(path)
        except EnvironmentError, e:
            raise MediaError("error while unlocking %s: %s" % (path, e))

    def packages_by_source(self, sourcename):
        from mediasys.hdlist import Package
        if self.srpms_by_name is None:
            try:
                self.load()
            except MetadataNotFound, e:
                logger.debug("assuming empty package list: %s", e)
                return
        srpms = {} # srcname : pkg
        found = self.srpms_by_name.get(sourcename, ())
        for info in found:
            fn = info["fn"] # fullname
            foundpkgs = self.pkgs_by_fullname.get(fn, ())
            for pkg in foundpkgs:
                srpms.setdefault(info["sourcerpm"], []).append(pkg)
        # another loop as the packages must be grouped by "sourcerpm"
        for srpm, pkgs in srpms.iteritems():
            name, _, _ = srpm.rsplit("-", 2)
            src = Package()
            src.name = name
            src.fullversion = pkgs[0].fullversion
            src.fullname = srpm
            pkgset = PackageSet(pkgs, src)
            yield pkgset

    def package_path(self, pkg):
        """Returns the path of a given package object"""
        # FIXME build path based on user configuration
        path = os.path.join(self.path, pkg.filename())
        return path

    def init(self):
        metapath = os.path.join(self.path, self.config.metadata_dirname)
        for path in (self.path, metapath):
            if not os.path.exists(path):
                try:
                    logger.debug("creating directory for media %s", path)
                    os.makedirs(path)
                except EnvironmentError, e:
                    raise MediaError("failed to create directory for "
                            "media %s, %s: %s" % (self.name, path, e))

    def update(self):
        args = self.config.get_genhdlist_command()
        args.append(self.path)
        logger.debug("updating medias with %s", args)
        output, _ = cmd.run(args)
        logger.debug("genhdlist repr(output): %r", output)

class Mediaset(object):

    def __init__(self, medias):
        self._medias = frozenset(medias)

    def medias(self):
        return self._medias

    def byname(self, name):
        for media in self._medias:
            if media.name == name:
                return media

    def bytag(self, name):
        return set(m for m in self._medias
                    if name in m.tags)

class TransactionError(Error):
    pass

class Transaction:

    def __init__(self, distro, config):
        self.config = config
        self.distro = distro
        self._remove_operations = []
        self._install_operations = []
        self.id = time.strftime("%Y%m%d%H%M%S") + "-" + str(id(self))
        basedir = self.config.recently_removed_dir
        self.storedir = os.path.join(basedir, self.id)

    def remove(self, media, pkgset, comment=None, touches=[]):
        self._remove_operations.append((media, pkgset, comment, touches))

    def install(self, media, pkgset, comment=None, touches=[]):
        self._install_operations.append((media, pkgset, comment, touches))

    def _exec_remove(self):
        for (mediainfo, pkgset, comment, touches) in self._remove_operations[:]:
            for pkg in pkgset.packages():
                srcpath = self.distro.package_path(mediainfo, pkg)
                srcdir = os.path.dirname(srcpath)
                filename = os.path.basename(srcpath)
                dstpath = os.path.join(self.storedir, filename)
                # TODO allow ignoring this kind of error
                if not os.path.exists(srcpath):
                    raise TransactionError("cannot find file: %s" %
                            (srcpath))
                if util.same_partition(self.storedir, srcdir):
                    logger.debug("renaming %s to %s", srcpath, dstpath)
                    try:
                        os.rename(srcpath, dstpath)
                    except EnvironmentError, e:
                        raise TransactionError("failed to move file from "
                                "%s to %s: %s" % (srcpath, dstpath, e))
                else:
                    cpcmd = self.config.get_copy_command()
                    cpcmd.append(srcpath)
                    cpcmd.append(dstpath)
                    logger.debug("running %s", cpcmd)
                    try:
                        cmd.run(cpcmd)
                    except cmd.CommandError, e:
                        raise TransactionError("failed to copy file from "
                            "%s to %s: %s" % (srcpath, dstpath, e))
                    logger.debug("unlinking %s", srcpath)
                    try:
                        os.unlink(srcpath)
                    except EnvironmentError, e:
                        raise TransactionError("failed to unlink %s: %s" %
                                (srcpath, e))

    def _exec_install(self):
        params = []
        for (media, pkgset, comment, touches) in self._install_operations[:]:
            for pkg in pkgset.packages():
                srcdir = os.path.dirname(pkg.path)
                if not os.path.exists(pkg.path):
                    raise TransactionError("cannot find %s" % (pkg.path))
                if not os.access(srcdir, os.W_OK):
                    raise TransactionError("no write permission for %s" %
                            (pkg.path))
                dstpath = self.distro.package_path(media, pkg)
                dstdir = os.path.dirname(os.path.abspath(dstpath))
                if not os.access(dstdir, os.W_OK):
                    raise TransactionError("no write permission for the "
                            "destination directory: %s" % (dstdir))
        paths = set()
        for (media, pkgset, comment, touches) in self._install_operations[:]:
            for pkg in pkgset.packages():
                if pkg.path in paths:
                    # prevent collision between operations that may involve
                    # the same file (the default install action vs. the
                    # debug package filter)
                    continue
                else:
                    paths.add(pkg.path)
                dstpath = self.distro.package_path(media, pkg)
                dstdir = os.path.dirname(os.path.abspath(dstpath))
                srcdir = os.path.dirname(os.path.abspath(pkg.path))
                if not os.path.exists(pkg.path):
                    raise TransactionError("cannot find file: %s" %
                            (pkg.path))
                if util.same_partition(srcdir, dstdir):
                    logger.debug("renaming %s to %s", pkg.path, dstpath)
                    try:
                        os.rename(pkg.path, dstpath)
                    except EnvironmentError, e:
                        raise TransactionError("failed to move file from "
                                "%s to %s: %s" % (pkg.path, dstpath, e))
                else:
                    cpcmd = self.config.get_copy_command()
                    cpcmd.append(pkg.path)
                    cpcmd.append(dstpath)
                    logger.debug("running command %s", cpcmd)
                    try:
                        cmd.run(cpcmd)
                    except cmd.CommandError, e:
                        raise TransactionError("failed to copy file from "
                            "%s to %s: %s" % (pkg.path, dstpath, e))
                try:
                    args = self.config.get_chmod_command()
                    args.append(self.config.package_copy_mode)
                    args.append(dstpath)
                    cmd.run(args)
                except cmd.CommandError, e:
                    raise TransactionError("failed to set permissions "
                            "for %s: %s" % (dstpath, e))

    def _medias_involved(self):
        medias = set()
        for ops in (self._install_operations, self._remove_operations):
            for (media, pkgset, _, touches) in ops:
                # XXX source
                for pkg in pkgset.packages():
                    medias.update(self.distro.urpmi_media_for(media, pkg))
                    for touched in touches:
                        medias.update(self.distro.urpmi_media_for(touched, pkg))
        return frozenset(medias)

    def _lock_medias(self):
        # FIXME if two processes start at the same time in a different
        # media order, there will happen a dead-lock
        for media in self._medias_involved():
            media.lock()

    def _unlock_medias(self):
        for media in self._medias_involved():
            media.unlock()

    def execute(self):
        # prepare a temporary working directory for the transaction
        try:
            os.makedirs(self.storedir)
        except EnvironmentError, e:
            raise TransactionError("failed to create the transaction "
                    "working directory %s: %s" % (self.storedir, e))
        self._lock_medias()
        try:
            self._exec_install()
            self._exec_remove()
            for media in self._medias_involved():
                media.update()
        finally:
            self._unlock_medias()
