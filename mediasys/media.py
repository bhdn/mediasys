import os
import shutil
import re
import time
import string
import subprocess
import itertools
import logging

from mediasys import Error, config

log = logging.getLogger("mediasys.media")

class CommandError(Error):
    pass

class MediaError(Error):
    pass

class FiltError(MediaError):
    pass

class PackageSetRejected(MediaError):
    pass

class RemoveError(MediaError):
    pass

EXPR_PROVIDES_VERSION = re.compile("(?P<name>.*?)(?:\[(?P<version>[^\]]+)\])?$")

class FauxRPMMacroTemplate(string.Template):
    delimiter = "%"

class Action:
    paths = []

    def __init__(self, paths):
        self.paths = paths

class InstallAction(Action): pass
class RemoveAction(Action): pass
class KeepAction(Action): pass

def cmd(args):
    log.debug("about to execute: %s" % (args))
    p = subprocess.Popen(args=args, shell=False, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
    p.wait()
    output = p.stdout.read()
    if p.returncode != 0:
        raise CommandError, "command %s failed with exit code %d: %s" % \
                (args, p.returncode, output)
    return (p.returncode, output)

class Media:

    def add_packages(self, path_or_package_instance):
        raise NotImplementedError

    def remove_packages(self, paths_or_packages):
        raise NotImplementedError

    def save(self):
        """Apply changes to repository"""
        raise NotImplementedError

    def load(self):
        raise NotImplementedError

def filter_upgrade_package(hpkg, media):
    #FIXME this is a silly way of inserting a newer package inside the
    # repository. It should ensure the new package has a higher version
    # number.
    old = media.packages_by_name.get(hpkg.name, [])
    actions = []
    for oldpkg in old:
        oldpath = media.package_file_name(oldpkg)
        actions.append(RemoveAction([oldpath]))
    if not oldpkg:
        log.debug("no older packages were found for %s-%s" % (hpkg.name,
            hpkg.fullversion))
    return actions

# TODO: move it inside MandrivaMedia
FILTERS = (filter_upgrade_package,)

class MandrivaMedia(Media):

    def __init__(self, path, mediaconf, globalconf, filters=set()):
        self.path = path
        self.mediaconf = mediaconf
        self.globalconf = globalconf
        self.added = []
        self.removed = []
        self.packages = None
        self.packages_by_name = {} # { name : hpkg, ...}
        self.packages_by_provides = {} # { providename : [hpkg,...], ...}
        if filters:
            self.filters = filters
        else:
            self.filters = FILTERS

    def add_packages(self, srcpaths):
        self._install_package(srcpaths, self.path)
        self.pending.extend(srcpaths)

    def create(self):
        if not os.path.exists(self.path):
            log.debug("creating directory for %s" % (self.path))
            os.makedirs(self.path)
        else:
            log.debug("create: directory %s already exists" % (self.path))
        self.save()

    def _generate_medias(self):
        args = [self.globalconf.genhdlist_cmd, "--allow-empty-media", self.path]
        log.info("updating metadata at %s" % (self.path))
        cmd(args)

    def _install_package(self, srcpaths, dstpath):
        mode = str(self.globalconf.package_copy_mode)
        args = [self.globalconf.install_cmd, "-m", mode]
        args.extend(srcpaths)
        args.append(dstpath)
        cmd(args)

    def _parse_provides(self, synthesis_provides):
        "Parses a provides entry in the synthesis hdlist format"
        found = EXPR_PROVIDES_VERSION.search(synthesis_provides)
        if not found:
            # DANGER! I actually don't know how to behave here
            return synthesis_provides, ""
        return found.group("name"), found.group("version")

    def load(self):
        from mediasys.hdlist import HdlistParser
        if self.packages is None:
            self.packages = set()
            if os.path.exists(self.path):
                log.info("parsing %s" % (self.path))
                parser = HdlistParser(self.path, self.globalconf)
                while True:
                    pkg = parser.next()
                    if pkg is None:
                        break
                    self.packages.add(pkg)
                    self.packages_by_name.setdefault(pkg.name,
                            []).append(pkg)
                    for synthprov in pkg.provides:
                        prov, version = self._parse_provides(synthprov)
                        self.packages_by_provides.setdefault(prov,
                                []).append(pkg)
            else:
                log.debug("%s doesn't exit, skipping loading metadata" %
                        (self.infodir))

    def save(self):
        self._generate_medias()

    def remove_by_file_name(self, names):
        prefix = time.strftime("%Y%m%d%H%M%S") + "-"
        for name in names:
            path = os.path.join(self.path, name)
            dstdir = self.globalconf.recently_removed_dir
            newname = prefix + name
            newpath = os.path.join(dstdir, newname)
            if not os.path.exists(dstdir):
                log.debug("creating %s" % (dstdir))
                os.makedirs(dstdir)
            log.info("disposing %s to %s (someone else should clean it up!)" \
                    % (path, newname))
            self.removed.append(path)
            self._install_package([path], newpath)
            log.debug("unlinking %s" % (path))
            os.unlink(path)

    def package_file_name(self, hpkg):
        tmpl = FauxRPMMacroTemplate(self.globalconf.rpmfile_fmt)
        tmpl.delimiter = "%"
        epoch = ""
        try:
            epoch, vr = hpkg.fullversion.split(":", 1)
        except ValueError:
            epoch = ""
            vr = hpkg.fullversion
        try:
            version, relarch = vr.split("-", 1)
            release, arch = relarch.rsplit(".", 1)
        except ValueError:
            raise MediaError, ("invalid package version: %s" %
                    (hpkg.fullversion))
        env = {"name": hpkg.name, "version": version, "release": release,
                "arch": arch}
        fname = tmpl.substitute(env)
        return fname

    def _execute_actions(self, actions):
        to_remove = set()
        to_install = set()
        to_keep = set()
        action_sets = {RemoveAction: to_remove,
                    InstallAction: to_install,
                    KeepAction: to_keep }
        for action in actions:
            action_sets[action.__class__].update(action.paths)
        log.debug("%s: to install: %s" % (self.path, " ".join(to_install)))
        log.debug("%s: to remove: %s" % (self.path, " ".join(to_remove)))
        log.debug("%s: to keep: %s" % (self.path, " ".join(to_keep)))
        to_remove.difference_update(to_keep)
        for file in itertools.chain(to_remove, to_install, to_keep):
            path = os.path.join(self.path, file)
            if not os.access(path, os.W_OK):
                errprefix = "action aborted: "
                if not os.path.exists(path):
                    errmsg = errprefix + "file not found: %s" % (path)
                else:
                    errmsg = errprefix + "cannot write to "\
                            "file: %s" % (path)
                log.error(errmsg)
                raise MediaError, errmsg
        # ordering: removing before as a way to handle systems with low
        # disk space
        self.remove_by_file_name(to_remove)
        self._install_package(to_install, self.path)
        self.added.extend(to_install)

    def put(self, paths):
        from mediasys.package import Pkg
        self.load()
        actions = [InstallAction(paths)]
        for path in paths:
            rpmpkg = Pkg(path)
            for filter in self.filters:
                actions.extend(filter(rpmpkg, self))
        self._execute_actions(actions)
