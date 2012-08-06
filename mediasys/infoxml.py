import os
import subprocess
import shlex
import logging
from mediasys import Error
from xml.etree import ElementTree

logger = logging.getLogger("mediays.infoxml")

class InfoxmlParseError(Error):
    pass

class InfoxmlParser:

    def __init__(self, basedir, config):
        self.path = os.path.join(basedir, config.metadata_dirname,
                config.info_xml_filename)
        self.lzcatcmd = shlex.split(config.lzcat_cmd)

    def _load_tree(self, path):
        cmd = self.lzcatcmd[:]
        cmd.append(path)
        if not os.path.exists(path):
            raise InfoxmlParseError, ("not found: %s" % (path))
        logger.debug("running %s", cmd)
        try:
            p = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
        except OSError, e:
            raise InfoxmlParseError, ("failed to run %s: %s" % (cmd, e))
        try:
            tree = ElementTree.parse(p.stdout)
        except ElementTree.ParseError, e:
            raise InfoxmlParseError, ("failed to load parse %s: %s" %
                    (path, e))
        p.wait()
        if p.returncode != 0:
            output = p.stderr.read()
            raise InfoxmlParseError, ("command failed %s: %s" % (cmd,
                output))
        return tree

    def load(self):
        tree = self._load_tree(self.path)
        try:
            found = tree.findall("info")
        except ElementTree.ParseError, e:
            raise InfoxmlParseError, ("failed to find <info> entries in "
                    "%s: %s" % (self.path, e))
        res = []
        for item in found:
            values = dict(item.items())
            values["descr"] = item.text
            res.append(values)
        return res
