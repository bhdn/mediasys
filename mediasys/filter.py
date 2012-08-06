import os
import logging
import re
import shlex
from mediasys import Error
from mediasys import cmd
from mediasys.registry import Registry
from mediasys.rpmver import vercmp
from mediasys.util import run_passphrase_command
from mediasys.media2 import PackageSet

logger = logging.getLogger("mediasys.filter")

class FilterError(Error):
    pass

class Filter(object):

    def __init__(self, config):
        self.config = config

    def check_package_set(self, pkgset):
        pass

    def suggest_media(self, pkgset, mediaconfs):
        pass

    def check_target_media(self, pkgset, mediaset, medianame):
        pass

    def filter(self, pkgset, trans, media, mediaset, archset):
        pass

class DefaultMedia(Filter):

    def suggest_media(self, pkgset, mediaconfs):
        found = mediaconfs.bytag("default")
        if len(found) > 1:
            names = ", ".join(f.name for f in found)
            raise FilterError("medias [%s] are marked as "
                    "default, but only one is allowed" % (names))
        elif found:
            media = tuple(found)[0]
            logger.debug("suggesting media %s", media.name)
            return media
        logger.debug("no default media set")
        return

class PackageList(Filter):

    def suggest_media(self, pkgset, mediaconfs):
        matches = []
        sourcename = pkgset.source().name
        for media in mediaconfs.medias():
            pkglist = media.value("packagelist")
            if pkglist:
                path = os.path.join(self.config.config_dir, pkglist)
                try:
                    if os.path.exists(path):
                        with open(path) as f:
                            names = frozenset(line.strip()
                                    for line in f.readlines())
                            if sourcename in names:
                                matches.append(media)
                except EnvironmentError, e:
                    raise FilterError("failed while trying to read the "
                            "file list %s: %s" % (path, e))

        if not matches:
            logger.debug(("there are no package lists referring to %s thus "
                "no media to suggest"), sourcename)
            return None
        elif len(matches) > 1:
            medianames = ", ".join(matches)
            # FIXME: that's a stupid restriction!
            raise FilterError, ("the medias [%s] refer the package %s "
                    "in their packagelists, but only one is allowed" %
                    (medianames, sourcename))
        else:
            return matches[0]

    def check_target_media(self, pkgset, mediaset, media):
        suggested = self.suggest_media(pkgset, mediaset)
        sugsec = suggested.value("section", None)
        medsec = media.value("section", None)
        if sugsec != medsec:
            raise FilterError("%s is only allowed on the "
                    "%s section" % (pkgset.source(), sugsec))

class Older(Filter):

    def filter(self, pkgset, trans, mediainfo, mediaset, archset):
        sourcename = pkgset.source().name
        for foundpkgset in mediainfo.packages_by_source(sourcename):
            foundver = foundpkgset.source().fullversion
            pkgsetver = pkgset.source().fullversion
            if vercmp(foundver, pkgsetver) < 0:
                trans.remove(mediainfo, foundpkgset,
                        comment=("obsoleted by %s" % (pkgset.source())))

class Release(Filter):

    def filter(self, pkgset, trans, mediainfo, mediaset, archset):
        if "release" in mediainfo.tags:
            for subname in ("updates", "testing"):
                for updmedia in mediaset.bytag(subname):
                    if updmedia.value("section") == mediainfo.value("section"):
                        setsfound = updmedia.packages_by_source(pkgset.source().name)
                        for pkgset in setsfound:
                            trans.remove(updmedia, pkgset,
                                        "replaced by %s on %s" %
                                        (pkgset.source(), mediainfo))

class RequiredArch(Filter):

    def filter(self, pkgset, trans, mediainfo, mediaset, archset):
        provided = set(pkg.arch for pkg in pkgset.packages())
        required = set(arch.name for arch in archset.medias()
                if "required" in arch.tags)
        diff = required.difference(provided)
        if diff:
            names = ", ".join(diff)
            raise FilterError("no packages for mandatory architectures were "
                    "provided: %s" % (names))

class Sign(Filter):

    def _get_passphrase(self):
        path = os.path.expanduser(self.config.resign_passphrase_file)
        try:
            if not os.path.exists(path):
                passphrase = ""
            else:
                with open(path) as f:
                    data = f.read(1024)
                    passphrase = data.lstrip()
        except EnvironmentError, e:
            raise FilterError("failed while trying to read the passphrase "
                    "file %s: %s" % (path, e))
        return passphrase

    def _get_command(self):
        cmd = self.config.get_resign_command()
        cmd.extend(("--define", "_signature %s" %
            (self.config.resign_signature)))
        cmd.extend(("--define", "_gpg_name %s" %
            (self.config.resign_gpg_name)))
        gpgpath = os.path.expanduser(self.config.resign_gpg_path)
        cmd.extend(("--define", "_gpg_path %s" % (gpgpath)))
        return cmd

    def filter(self, pkgset, trans, mediainfo, mediaset, archset):
        cmd = self._get_command()
        cmd.extend(pkg.path for pkg in pkgset.packages())
        cmd.append(pkgset.source().path)
        prompt = self.config.resign_command_prompt
        passphrase = self._get_passphrase()
        logger.debug("running with passphrase: %s", cmd)
        run_passphrase_command(cmd, passphrase, prompt)

class Debug(Filter):

    def __init__(self, *args, **kwargs):
        super(Debug, self).__init__(*args, **kwargs)
        try:
            self.group_re = re.compile(self.config.debug_group_re)
        except re.error, e:
            raise FilterError("failed to compile the debug group "
                    "regular expression %r: %s" %
                    (self.config.debug_group_re, e))
        try:
            self.name_re = re.compile(self.config.debug_name_re)
        except re.error, e:
            raise FilterError("failed to compile the debug name "
                    "regular expression %r: %s" %
                    (self.config.debug_name_re, e))
        fields = shlex.split(self.config.debug_target_media)
        if len(fields) < 2:
            raise FilterError("debug-target-media requires two fields")
        target_expr = fields[0]
        self.target_repl = fields[1]
        try:
            self.target_re = re.compile(target_expr)
        except re.error, e:
            raise FilterError("failed to compile the debug target "
                    "regular expression %r: %s" %
                    (target_expr, e))

    def _debug_name(self, medianame):
        return self.target_re.sub(self.target_repl, medianame)

    def filter(self, pkgset, trans, mediainfo, mediaset, archset):
        for pkg in pkgset.packages():
            if (self.group_re.search(pkg.group)
                    and self.name_re.search(pkg.name)):
                target = self._debug_name(mediainfo.name)
                media = mediaset.byname(target)
                if media is None:
                    raise FilterError("didn't find target debug media %r, "
                            "check if debug-target-media is correct" %
                            (target))
                newpkgset = PackageSet(packages=set((pkg,)))
                trans.install(media, newpkgset, "debug package")

    def move(self, pkgset, trans, srcmedia, dstmedia, mediaset, archset):
        medianame = self._debug_name(srcmedia.name)
        mediainfo = mediaset.byname(medianame)
        if mediainfo is not None:
            sourcename = pkgset.source().name
            for cand in mediainfo.packages_by_source(sourcename):
                if cand.source().fullversion == pkgset.source().fullversion:
                    newname = self._debug_name(dstmedia.name)
                    newmedia = mediaset.byname(newname)
                    if newmedia:
                        trans.install(newmedia, cand, 
                            "moving debug packages",
                            touches=(mediainfo,))
                    else:
                        logger.debug("cannot find target debug media %r",
                                newname)

filters = Registry("layout package filter")
filters.register("default-media", DefaultMedia)
filters.register("package-list", PackageList)
filters.register("required-arch", RequiredArch)
filters.register("older", Older)
filters.register("release", Release)
filters.register("sign", Sign)
filters.register("debug", Debug)

def get_filter(name, distroconf):
    return filters.get_instance(name, distroconf)
