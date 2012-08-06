import os
from os.path import join
from tests import Test
from mediasys import distro as distromod
from mediasys.config import MediasysConfig
from mediasys.media2 import URPMIMedia, Transaction

class TestTransaction(Test):

    media_class = URPMIMedia

    def get_media_config(self, root):
        config = MediasysConfig()
        distroconf = config.get_any_distro()
        layoutconf = config.get_any_layout()
        distroconf.root = root
        distroconf.recently_removed_dir = self.recently_removed_dir
        distro = distromod.get_distro(distroconf, layoutconf, config)
        config.recently_removed_dir = self.testrecentlyremoved_dir
        media = self.media_class(self.testrepomainrelease_dir, distroconf)
        return media, distroconf, distro

    def test_remove(self):
        root = self.testrepomainrelease_dir
        media, distroconf, distro = self.get_media_config(root=root)
        media.load()
        t = Transaction(distro, distroconf)
        pkgset = media.packages_by_source("null-a").next()
        t.remove(media, pkgset, "removing a set of packages")
        t.execute()
        for pkg in pkgset.packages():
            oldpath = media.package_path(pkg)
            filename = os.path.basename(oldpath)
            newpath = os.path.join(self.testrecentlyremoved_dir,
                    t.storedir, filename)
            self.assertTrue(os.path.exists(newpath),
                    "%s not found" % (newpath))

    def test_install(self):
        root = self.testrepomainrelease_dir
        media, distroconf, distro = self.get_media_config(root=root)
        media.load()
        t = Transaction(distro, distroconf)
        pkgset = media.packages_by_source("null-a").next()
        t.install(media, pkgset, "installing a package set into the repo")
        t.execute()
        for pkg in pkgset.packages():
            oldpath = pkg.path
            newpath = media.package_path(pkg)
            self.assertTrue(os.path.exists(newpath), 
                    "%s not found" % (newpath))

