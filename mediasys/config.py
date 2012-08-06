from cStringIO import StringIO
import shlex
import re
import ConfigParser
from mediasys import defaults, Error
import logging

log = logging.getLogger("mediasys.config")

class ConfigError(Error):
    pass

class SectionWrapper(object):

    _config = None
    _section = None

    def __init__(self, parent, section, defaultssec=None):
        self._config = parent.config_object()
        self._parent = parent
        self._section = section
        self._defaultssec = defaultssec

    def __getattr__(self, name):
        try:
            return self._config.get(self._section, name)
        except ConfigParser.NoOptionError:
            try:
                nicename = name.replace("_", "-")
                return self._config.get(self._section, nicename)
            except (AttributeError, ConfigParser.NoOptionError):
                if self._defaultssec is not None:
                    return getattr(self._defaultssec, name)
                else:
                    raise AttributeError(name)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            self._config.set(self._section, name, value)

class Config(object):

    _section = None
    _config = None
    _sections = None

    def __init__(self):
        self._config = ConfigParser.ConfigParser()
        self._sections = {}

    def config_object(self):
        return self._config

    def __repr__(self):
        output = StringIO()
        self._config.write(output)
        return output.getvalue()

    def __getattr__(self, name):
        try:
            section = self._sections[name]
        except KeyError:
            try:
                # configuration-names-look-better-using-dashes-than
                # underscores_that_look_like_a_programming_mindset_leak
                nicename = name.replace("_", "-")
                section = self._sections[nicename]
            except KeyError:
                chosen = None
                if name in self._config.sections():
                    chosen = name
                elif nicename in self._config.sections():
                    chosen = nicename
                else:
                    raise AttributeError, name
                section = SectionWrapper(self, chosen)
                self._sections[chosen] = section
        return section

    def get_section(self, name, defaultsname=None):
        return SectionWrapper(self, name, getattr(self, defaultsname))

    def merge(self, data):
        for section, values in data.iteritems():
            for name, value in values.iteritems():
                self._config.set(section, name, value)

    def parse(self, raw):
        self._config.readfp(StringIO(raw))

    def load(self, path):
        self._config.readfp(open(path))


class Layoutconf(SectionWrapper):

    def get_plugins(self):
        return self.plugins.split(None)

    def _split_tags_values(self, rawtags):
        fields = shlex.split(rawtags)
        tags = set()
        values = {}
        for field in fields:
            if "=" in field:
                name, value = field.split("=", 1)
                values[name] = value
            else:
                tags.add(field)
        return tags, values

    def get_install_filters(self):
        return shlex.split(self.install_filters)

    def get_move_filters(self):
        return shlex.split(self.move_filters)

    def get_medias(self):
        return self._parse_conf("media", "medias")

    def get_arches(self):
        return self._parse_conf("arch", "arches")

    def get_directory_structure(self):
        return self.directory_structure.split()

    def _parse_conf(self, conftag, nametag):
        """Parses the 'media description language'

        Basically it allows setting configuration values and tags to each
        media. One is able to assign values to many medias by using regular
        expressions in "media" entries while "medias" defines the real
        media names.

          media [^/]+/release = release
          medias = main/release main/contrib
        """
        expressions = []
        medias = set()
        # collect media names and configuration expressions
        for opt in self._config.options(self._section):
            fields = opt.split(None, 1)
            value = self._config.get(self._section, opt)
            if len(fields) == 2 and fields[0] == conftag:
                # media <expr> = tags...
                expressions.append((fields[1], value))
            elif opt == nametag:
                # medias = media/name
                names = shlex.split(value)
                medias.update(names)
        # compile regexps
        compiled = []
        for expr, rawtags in expressions:
            try:
                comp = re.compile(expr)
            except re.error, e:
                raise ConfigError("failed to parse the regexp used in media "
                        "definition %r: %s" % (expr, e))
            compiled.append((comp, rawtags))
        # match regexps and assign tags and values to each media
        mediasconf = {}
        for media in medias:
            mediasconf[media] = (set(), {})
        for media in medias:
            for i, (expr, rawtags) in enumerate(compiled):
                if expr.match(media):
                    # by using shlex we allow the use of spaces in values
                    # and tags
                    tags, values = self._split_tags_values(rawtags)
                    conf = mediasconf[media]
                    conf[0].update(tags)
                    conf[1].update(values)
        return mediasconf

class Distroconf(SectionWrapper):

    def _split_conf(self, secname, optname):
        rawconf = self._config.get(secname, optname)
        fields = shlex.split(rawconf)
        conf = {}
        for rawconf in fields:
            try:
                conffields = rawconf.split("=", 1)
            except ValueError:
                raise ConfigError, ("invalid configuration in option %s from "
                        "section %s: %r" % (optname, secname, rawconf))
            if len(conffields) == 1:
                value = None
            else:
                value = conffields[1]
            conf[conffields[0]] = value
        return conf

    def get_layout(self):
        secname = "layout %s" % (self.layout)
        layoutconf = SectionWrapper(self, secname)
        return layoutconf

    def get_resign_command(self):
        return shlex.split(self.resign_command)

    def get_copy_command(self):
        return shlex.split(self.copy_command)

    def get_genhdlist_command(self):
        return shlex.split(self.genhdlist_command)

    def get_chmod_command(self):
        return shlex.split(self.chmod_command)

    def get_smart_command(self, datadir, subcmd, args):
        cmd = shlex.split(self.smart_command)
        cmd.append(subcmd)
        cmd.extend(shlex.split(self.smart_options))
        cmd.append("--data-dir")
        cmd.append(datadir)
        cmd.extend(args)
        return cmd
        
class MediasysConfig(Config):

    def __init__(self):
        super(MediasysConfig, self).__init__()
        self.parse(defaults.CONFIG_DEFAULTS)
        self._layoutconfs = self._load_layout_confs()
        self._anydistro = Distroconf(self, "any distro", None)
        self._anylayout = Layoutconf(self, "any layout", None)

    def get_distro(self, name, root=None):
        """Parses configuration and finds all distributions in media
        configuration"""
        from mediasys.distro import get_distro, Distroset, NoSuchDistro
        for secname in self._config.sections():
            fields = secname.split(None, 1)
            if len(fields) > 1 and fields[0] == "distro":
                candname = fields[1]
                if name != candname:
                    continue
                distroconf = Distroconf(self, secname, self._anydistro)
                distroconf.name = name
                if root is not None:
                    # why not more options?
                    distroconf.root = root
                try:
                    layoutconf = self._layoutconfs[distroconf.layout]
                except KeyError:
                    raise ConfigError("unknown layout %r, referred by "
                            "distro %r" % (name, distroconf.layout))
                distro = get_distro(distroconf, layoutconf, self)
                return distro
        raise NoSuchDistro

    def get_any_distro(self):
        return self._anydistro

    def get_any_layout(self):
        return self._anylayout

    def _load_layout_confs(self):
        layouts = {}
        anylayout = SectionWrapper(self, "any layout")
        for secname in self._config.sections():
            fields = secname.split(None, 1)
            if len(fields) > 1 and fields[0] == "layout":
                name = fields[1]
                secname = "layout %s" % (name)
                layouts[name] = Layoutconf(self, secname, anylayout)
        return layouts
