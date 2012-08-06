import os

from tests import Test

from mediasys.config import MediasysConfig
import mediasys.hdlist

class TestHdlist(Test):

    def test_create_instance(self):
        distroconf = MediasysConfig().get_any_distro()
        basedir = self.testrepomainrelease_dir
        parser = mediasys.hdlist.HdlistParser(basedir, distroconf)

    def test_load_all(self):
        self._load_packages()

    def _load_packages(self, rpm5=False):
        distroconf = MediasysConfig().get_any_distro()
        if rpm5:
            basedir = self.rpm5_testrepomainrelease_dir
        else:
            basedir = self.testrepomainrelease_dir
        parser = mediasys.hdlist.HdlistParser(basedir, distroconf)
        pkgs = []
        while True:
            pkg = parser.next()
            if pkg is None:
                break
            pkgs.append(pkg)
        return pkgs

    def test_load_packages(self):
        pkgs = self._load_packages()
        self.assertEqual(len(pkgs), 10)
        self.assertEquals(pkgs[0].name, "null-bar")
        self.assertEquals(pkgs[1].name, "etcskel")
        self.assertEquals(pkgs[2].name, "mandriva-lxde-config-Free")
        self.assertEquals(pkgs[3].name, "null-foo")
        self.assertEquals(pkgs[4].name, "null-a-bummy")
        self.assertEquals(pkgs[5].name, "null-a")
        self.assertEquals(pkgs[6].name, "t1lib-config")
        self.assertEquals(pkgs[7].name, "null-a-gummy")
        self.assertEquals(pkgs[8].name, "null-a-dummy")
        self.assertEquals(pkgs[9].name, "null-a-debug")
        self.assertEqual(pkgs[0].fullversion, "1:2.1-34bog2011.0.i586")
        self.assertEqual(pkgs[1].fullversion, "0:1.63-27mdv2011.0.noarch")
        self.assertEqual(pkgs[2].fullversion, "0:0.5-2mdv2010.1.noarch")
        self.assertEqual(pkgs[3].fullversion, "1:2.1-34bog2011.0.i586")
        self.assertEqual(pkgs[4].fullversion, "1:2.1-72.i586")
        self.assertEqual(pkgs[5].fullversion, "1:2.1-72.i586")
        self.assertEqual(pkgs[6].fullversion, "1:5.1.2-13.i586")
        self.assertEqual(pkgs[7].fullversion, "1:2.1-72.i586")
        self.assertEqual(pkgs[8].fullversion, "1:2.1-72.i586")
        self.assertEqual(pkgs[9].fullversion, "1:2.1-72.i586")

    def test_get_package_after_load(self):
        distroconf = MediasysConfig().get_any_distro()
        basedir = self.testrepomainrelease_dir
        parser = mediasys.hdlist.HdlistParser(basedir, distroconf)
        self.assertNotEqual(parser.get("null-bar"), None)
