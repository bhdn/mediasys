import os
import logging
from mediasys import Error
from mediasys import filter
from mediasys.registry import Registry
from mediasys.media2 import MediaInfo, Mediaset, URPMIMedia, Transaction

logger = logging.getLogger("mediasys.distro")

class DistroError(Error):
    pass

class NoSuchDistro(DistroError):
    pass

class Distroset(dict):

    def __getitem__(self, name):
        try:
            return dict.__getitem__(self, name)
        except KeyError:
            raise NoSuchDistro, "no such distribution: " + name

class Distro(object):
    """A set of Medias + some policy to define packages' target medias """

    def __init__(self, distroconf, layoutconf, globalconf):
        self.distroconf = distroconf
        self.layoutconf = layoutconf
        self.globalconf = globalconf

    def choose_media_for(self, pkgset):
        """Gives the target media for a given package
        
        @pkgset: a mediays.media2.PackageSet"""
        raise NotImplementedError

    def put(self, files, medianame):
        raise NotImplementedError

class MandrivaDistro(Distro):

    def __init__(self, distroconf, layoutconf, globalconf):
        super(MandrivaDistro, self).__init__(distroconf, layoutconf,
                globalconf)
        self.mediaconfs = self._make_confset(layoutconf.get_medias())
        self.archconfs = self._make_confset(layoutconf.get_arches())
        self._urpmi_medias, self._media_matchers = self._create_urpmi_medias()
        self._bind_urpmi_medias()
        self._install_filters = self._load_install_filters(layoutconf)
        self._move_filters = self._load_move_filters(layoutconf)

    def _make_confset(self, mediasconf):
        medias = set()
        for name, (tags, values) in mediasconf.iteritems():
            media = MediaInfo(name)
            for tag in tags:
                media.set_tag(tag)
            for key, value in values.iteritems():
                media.set_value(key, value)
            medias.add(media)
        return Mediaset(medias)

    def _bind_urpmi_medias(self):
        for media in self.mediaconfs.medias():
            for urpmi in self.urpmi_media_for(media):
                media.add_real_media(urpmi)

    def _create_urpmi_medias(self):
        # be thankful if you didn't have to understand what this method
        # does
        components = self.layoutconf.get_directory_structure()
        done = []
        matchers = []
        medias = set()
        def f(base, comps, pos):
            comp = comps[pos]
            if comp == "root":
                tail = [("root", (self.distroconf.root, self))]
                return f(base + tail, comps, pos + 1)
            elif comp == "arch":
                for arch in self.archconfs.medias():
                    basedir = arch.value("basedir")
                    if basedir:
                        path = os.path.join(basedir, arch.name)
                    else:
                        path = arch.name
                    f(base + [("arch", (path, arch))], comps, pos + 1)
            elif comp == "media":
                for media in self.mediaconfs.medias():
                    basedir = media.value("basedir")
                    if basedir:
                        path = os.path.join(basedir, media.name)
                    else:
                        path = media.name
                    f(base + [("media", (path, media))], comps, pos + 1)
            elif comp == "package":
                path = os.path.sep.join(c[1][0] for c in base)
                urpmi = URPMIMedia(path, self.distroconf)
                medias.add(urpmi)
                base.append(("urpmi", (None, urpmi)))
                matchers.append(dict(base))
                done.append(base)
        f([], components, 0)
        return medias, matchers

    def _load_install_filters(self, layoutconf):
        filters = []
        for fname in layoutconf.get_install_filters():
            filters.append(filter.get_filter(fname, self.distroconf))
        return filters

    def _load_move_filters(self, layoutconf):
        filters = []
        for fname in layoutconf.get_move_filters():
            filters.append(filter.get_filter(fname, self.distroconf))
        return filters

    def _load_move_filters(self, layoutconf):
        filters = []
        for fname in layoutconf.get_move_filters():
            filters.append(filter.get_filter(fname, self.distroconf))
        return filters

    def choose_media_for(self, pkgset):
        """Gives the target media for a given package
        
        @pkgset: a mediays.media2.PackageSet"""
        chosen = None
        for filter in self._install_filters:
            answer = filter.suggest_media(pkgset, self.mediaconfs)
            if answer is not None:
                chosen = answer
        if chosen is None:
            name = self.layoutconf.default_media
            chosen = self.mediaconfs.byname(name)
            logger.debug("no filters provided a suggested media for %s, "
                    "relying on default-media %r", pkgset.source().name,
                    name)
        return chosen

    def urpmi_media_for(self, mediainfo, pkg=None):
        matchmedia = False
        matches = set()
        for matcher in self._media_matchers:
            for name, (path, obj) in matcher.iteritems():
                if (pkg is not None and name == "arch"
                        and obj.name != pkg.arch):
                    break
                elif name == "media" and obj.name != mediainfo.name:
                    break
            else:
                # nothing "did not match", so we can use this media this is
                # important in cases where there's only one media using
                # directory layout as 'root package', as it will never
                # match a media name nor an arch name
                matches.add(matcher["urpmi"][1])
        return frozenset(matches)

    def package_path(self, mediainfo, pkg):
        for urpmi in self.urpmi_media_for(mediainfo, pkg):
            return urpmi.package_path(pkg)
        raise DistroError("no urpmi media bound for %s (A BUG!)" %
                (mediainfo.name))

    def put(self, pkgset, medianame=None):
        if not medianame:
            media = self.choose_media_for(pkgset)
        else:
            media = self.mediaconfs.byname(medianame)
            for filter in self._install_filters:
                filter.check_media(pkgset, self.mediaconfs, media)
        trans = Transaction(self, self.distroconf)
        for filter in self._install_filters:
            filter.filter(pkgset, trans, media, self.mediaconfs,
                    self.archconfs)
        trans.install(media, pkgset, "msys-put")
        trans.execute()

    def move(self, sourcename, frommedia, tomedia):
        f_mediainfo = self.mediaconfs.byname(frommedia)
        t_mediainfo = self.mediaconfs.byname(tomedia)
        if f_mediainfo is None:
            raise DistroError("unknown source media %r" % (frommedia))
        if t_mediainfo is None:
            raise DistroError("unknown destination media %r" % (tomedia))
        trans = Transaction(self, self.distroconf)
        found = list(f_mediainfo.packages_by_source(sourcename))
        if not found:
            raise DistroError("package %r not found" % (sourcename))
        for pkgset in found:
            for filter in self._move_filters:
                filter.move(pkgset, trans, f_mediainfo, t_mediainfo,
                        self.mediaconfs, self.archconfs)
            msg = "moving %s-%s from %s to %s" % (sourcename,
                    pkgset.source().fullversion, frommedia, tomedia)
            trans.install(t_mediainfo, pkgset, msg, touches=(f_mediainfo,))
        trans.execute()

    def init(self):
        for media in self._urpmi_medias:
            media.init()

    def update(self, medianame=None):
        if medianame:
            medias = [self.mediaconfs.byname(medianame)]
        else:
            medias = self.mediaconfs.medias()
        for media in self._urpmi_medias:
            media.update()

distro_types = Registry("distro type")
distro_types.register("mandriva", MandrivaDistro)

def get_distro(distroconf, layoutconf, globalconf):
    klass = distro_types.get_class(distroconf.type)
    distro = klass(distroconf, layoutconf, globalconf)
    return distro
