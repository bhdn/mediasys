import glob
import logging

from mediasys import CliError
from mediasys.media2 import PackageSet

log = logging.getLogger("mediasys.facade")

class MediasysFacade:

    def __init__(self, mconfig):
        self.config = mconfig

    def put(self, files, distro=None, media=None, root=None):
        """Imports a set of packages to a target repository

        @files: A sequence of files to be imported
        @distro: target distribution name (defaults to main development
        distro, usually "cooker")
        @media: target media name (if not provided, falls back to the most
        recent one, or a default specicied in distro configuration.)
        """
        if distro is None:
            distro = self.config.mediasys.default_distro
        tdistro = self.config.get_distro(distro, root)
        if root:
            # FIXME WRONG either distroconf or distro should be
            # instantiated with this new root set
            tdistro.distroconf.root = root
        pkgset = PackageSet.from_filenames(files)
        tdistro.put(pkgset, media)

    def move(self, sourcename, distro=None, frommedia=None, tomedia=None):
        if distro is None:
            distro = self.config.mediasys.default_distro
        tdistro = self.config.get_distro(distro)
        tdistro.move(sourcename, frommedia, tomedia)

    def init(self, distro=None):
        """Creates the directory structure neede by a repository

        @distro: target distribution name (defaults to main development
        distro, usually "cooker")
        """
        if distro is None:
            distro = self.config.mediasys.default_distro
        tdistro = self.config.get_distro(distro)
        tdistro.init()

    def update(self, distro=None, media=None):
        """Updates repository metadata for a distribution or specific
        media

        @distro: target distribution name (defaults to main development
        distro, usually "cooker")
        @media: target media name (if not provided, falls back to the most
        """
        if distro is None:
            distro = self.config.mediasys.default_distro
        tdistro = self.config.get_distro(distro)
        tdistro.update(media)
