import logging
from mediasys import cmd
from medisys.filter import Filter, FilterError, filters

logger = logging.getLogger("mediasys.filter.smartcheck")

class SmartCheck(Filter):

    def _find_base_medias(self, mediainfo, mediaset):
        # we use uses-sections here just because Release already needs a
        # "section" value
        secs = frozenset(mediainfo.value("uses-sections").split(","))
        subsecs = frozenset(mediainfo.value("uses").split(","))
        for candidate in self.mediaset.medias():
            if (candidate.value("section") in secs and
                    candidate.tags.intersection(subsecs)):
                yield candidate

    def _make_channel_name(self, mediainfo):
        base = mediainfo.arch + ":" + mediainfo.name
        return base.replace("/", "_")

    def _check_workdir(self):
        path = os.path.join(self.config.smartcheck_workdir,
                self.config.smartcheck_datadirs_dir,
                self.config.name)
        try:
            if not os.path.exists(path):
                os.makedirs(path)
        except EnvironmentError, e:
            raise FilterError("failed to create working directory for "
                    "the smart-check filter %s: %s" % (path, e))
        return path

    def _symlink_packages(self, mediadir, pkgset):
        try:
            os.makedirs(mediadir)
        except EnvironmentError, e:
            raise FilterError("failed to create temporary media "
                    "directory %s: %s" % (mediadir, e))
        for pkg in pkgset.packages():
            src = os.path.abspath(pkg.path)
            name = os.path.basename(pkg.path)
            dst = os.path.join(mediadir, name)
            logger.debug("creating symlink from %s to %s", src, dst)
            try:
                os.symlink(src, dst)
            except EnvironmentError, e:
                raise FilterError("fail to create symlink from %s to "
                        "%s: %s" % (src, dst, e))

    def _create_tmp_media(self, topdir, pkgset):
        basedir = os.path.join(topdir, self.config.smartcheck_tmp_media_dir)
        tmpname = time.strftime("%Y%m%d%H%M%S") + "-" + str(id(self))
        mediadir = os.path.join(basedir, tmpname)
        self._symlink_packages(mediadir, pkgset)
        args = self.config.get_genhdlist_command()
        args.append(mediadir)
        cmd.run(args) # let it throw CommandError
        return mediadir

    def _ensure_smart_medias_exist(self, topdir, mediaset):
        import yaml
        datadir = os.path.join(topdir, self.config.smartcheck_datadir)
        args = self.config.get_smart_command(datadir, "channel", ["--yaml"])
        logger.debug("running %s", args)
        output, status = cmd.run(args)
        medianames = frozenset(self._make_channel_name(mi)
                                for mi in mediaset.medias())
        try:
            smartmedias = yaml.load(output)
        except yaml.YAMLError, e:
            raise FilterError("failed to parse YAML smart output: %s" %
                    (e))
        # XXX ver a midias q nao estao na saida do smart e tentar adicionar

    def filter(self, pkgset, trans, mediainfo, mediaset, archset):
        # - run genhdlist for the packages, leaving synthesis in a separate
        # repo (maybe create symlinks to have them in a single dir for
        # sure)
        # - if exists, remove the media 'candidate'
        # - create a media 'candidate' pointing to the temporary metadata
        #   directory
        # - ensure that all medias that are required by the target media
        #   exist, if not add and update them
        # - run smart check using the needed medias and candidate
        topdir = self._prepare_workdir()
        tmpmediadir = self._create_tmp_media(topdir, pkgset)
        self._ensure_smart_medias_exist(topdir, mediaset)

filters.register("smartcheck", SmartCheck)
