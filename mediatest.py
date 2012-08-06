from mediasys.config import Config

class Filter:

    def __init__(config):
        pass

    def check_package_set(self, pkgset):
        pass

    def suggest_media(self, pkgset, trans, mediaset):
        raise NotImplementedError

    def filter(self, pkgset, trans, media, mediaset):
        raise NotImplementedError

class PackageList(Filter):

    def suggest_media(self, pkgset, trans, mediaset):
        matches = []
        sourcename = pkgset.source().name
        for media in mediaset.medias():
            pkglist = media.value("packagelist")
            if pkglist:
                path = os.path.join(self.config.config_dir, pkglist)
                with open(path) as f:
                    names = frozenset(line.strip()
                            for line in f.readlines())
                    if sourcename in names:
                        matches.append(media)
        if len(matches) != 1:
            medianames = ", ".join(matches)
            raise FilterError, ("all these medias have the package %s "
                    "in their packagelists: %s, but only one should have" % 
                    (sourcename, medianames))
        elif matches:
            return matches[0]

class Older(Filter):

    def filter(self, pkgset, trans, media, mediaset):
        for foundpkgset in media.packages_by_source(pkgset.source()):
            if foundpkgset.source() < pkgset.source():
                trans.remove(media, foundpkgset,
                        comment=("obsoleted by %s" % (pkgset.source())))

class Release(Filter):

    def filter(self, pkgset, trans, media, mediaset):
        if "release" in media.tags:
            for subname in ("updates", "testing"):
                for updmedia in mediaset.bytag(subname):
                    if updmedia.value("section") == media.value("section"):
                        pkgfound = updmedia.packages_by_source(pkgset.source())
                        trans.remove(updmedia, pkgfound,
                                    (pkgset.source(), media))

class Media:

    def __init__(self):
        self.tags = set()
        self.values = {}

    def value(self, attrname):
        pass

    def packages_by_source(self, sourcepkg):
        pass

    def set_tag(self, name):
        self.tags.add(name)

    def set_value(self, name, value):
        self.values[name] = value

class Mediaset:

    def bytag(self, name):
        pass

class Distro:

    pass

class Transaction:

    def __init__(self, pkgset):
        pass

    def remove(self, srcmedia, pkgset, comment=None):
        pass
