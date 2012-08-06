import os

from tests import Test
import mediasys.config
import mediasys.media

class TestMedia(Test):

    def test_create_instance(self):
        distroconf = mediasys.config.MediasysConfig().get_any_distro()
        media = mediasys.media.MandrivaMedia(self.testrepomainrelease_dir,
                {}, distroconf)

    def test_load_some(self):
        distroconf = mediasys.config.MediasysConfig().get_any_distro()
        media = mediasys.media.MandrivaMedia(self.testrepomainrelease_dir,
                {}, distroconf)
        media.load()
        self.assertEquals(len(media.packages), 10)

    def test_cmd_success(self):
        status, output = mediasys.media.cmd(["true"])
        self.assertEquals(status, 0)
        self.assertEquals(output, "")

    def test_cmd_fail(self):
        self.assertRaises(mediasys.media.CommandError, mediasys.media.cmd,
                ["false"])

    def test_save(self):
        distroconf = mediasys.config.MediasysConfig().get_any_distro()
        media = mediasys.media.MandrivaMedia(self.testrepocontribrelease_dir, {},
                distroconf)
        media.load()
        media.save()

    def test_packages_by_name(self):
        distroconf = mediasys.config.MediasysConfig().get_any_distro()
        media = mediasys.media.MandrivaMedia(self.testrepomainrelease_dir,
                {}, distroconf)
        media.load()
        pkg = media.packages_by_name["etcskel"][0]
        self.assertEquals(pkg.fullversion, "0:1.63-27mdv2011.0.noarch")
        pkg = media.packages_by_name["mandriva-lxde-config-Free"][0]
        self.assertEquals(pkg.fullversion, "0:0.5-2mdv2010.1.noarch")
        pkg = media.packages_by_name["t1lib-config"][0]
        self.assertEquals(pkg.fullversion, "1:5.1.2-13.i586")

    def test_package_file_name(self):
        distroconf = mediasys.config.MediasysConfig().get_any_distro()
        media = mediasys.media.MandrivaMedia(self.testrepomainrelease_dir,
                {}, distroconf)
        media.load()
        pkg = media.packages_by_name["etcskel"][0]
        self.assertEquals(media.package_file_name(pkg),
                    "etcskel-1.63-27mdv2011.0.noarch.rpm")
        pkg = media.packages_by_name["mandriva-lxde-config-Free"][0]
        self.assertEquals(media.package_file_name(pkg),
                    "mandriva-lxde-config-Free-0.5-2mdv2010.1.noarch.rpm")
        pkg = media.packages_by_name["t1lib-config"][0]
        self.assertEquals(media.package_file_name(pkg),
                    "t1lib-config-5.1.2-13.i586.rpm")

    def test_packages_by_provides(self):
        distroconf = mediasys.config.MediasysConfig().get_any_distro()
        media = mediasys.media.MandrivaMedia(self.testrepomainrelease_dir,
                {}, distroconf)
        media.load()
        pkgs = media.packages_by_provides["etcskel"]
        self.assertEquals(len(pkgs), 1)
        self.assertEquals(pkgs[0].name, "etcskel")
        pkgs1 = media.packages_by_provides["t1lib-config"]
        self.assertEquals(len(pkgs1), 1)
        self.assertEquals(pkgs1[0].name, "t1lib-config")
        pkgs2 = media.packages_by_provides["t1lib-config"]
        self.assertEquals(len(pkgs2), 1)
        self.assertEquals(pkgs2[0].name, "t1lib-config")
        # questionable... VM-dependent:
        self.assertTrue(pkgs1[0] is pkgs2[0])
        # many packages providing the same name:
        pkgs = media.packages_by_provides["null"]
        self.assertEquals(pkgs[0].name, "null-bar")
        self.assertEquals(pkgs[1].name, "null-foo")
        self.assertRaises(KeyError, media.packages_by_provides.__getitem__,
                "should not exist")
        self.assertRaises(KeyError, media.packages_by_name.__getitem__,
                "should not exist")

    def test_put(self):
        distroconf = mediasys.config.MediasysConfig().get_any_distro()
        distroconf.recently_removed_dir = self.testrecentlyremoved_dir
        media = mediasys.media.MandrivaMedia(self.testrepomainrelease_dir,
                {}, distroconf)
        media.load()
        media.put([self.testpkgnew_path])
        media.save()
        media = mediasys.media.MandrivaMedia(self.testrepomainrelease_dir,
                {}, distroconf)
        media.load()
        pkgs = media.packages_by_name["null-bar"]
        self.assertEquals(len(pkgs), 1)
        pkg = pkgs[0]
        self.assertEquals(pkg.fullversion, "1:2.2-34bog2011.0.i586", "newer package "
                    "did not appear in repository metadata")
        self.assertEquals(len(media.packages), 10)
