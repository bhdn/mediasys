import os
from os.path import join
from tests import Test
from mediasys.config import MediasysConfig
from mediasys.media2 import MediaInfo, Mediaset, URPMIMedia

class TestMediaInfo(Test):

    media_class = MediaInfo
    synthesis_path = None

    def get_media(self):
        config = MediasysConfig()
        name = "test"
        m = self.media_class(name)
        return m

    def test_tags(self):
        m = self.get_media()
        m.set_tag("tag1")
        m.set_tag("tag2")
        self.assertTrue("tag1" in m.tags)
        self.assertTrue("tag2" in m.tags)
        self.assertFalse("tag3" in m.tags)

    def test_values(self):
        m = self.get_media()
        m.set_value("name1", "value1")
        m.set_value("name2", "value2")
        m.set_value("name3", "value3")
        self.assertEquals(m.value("name3"), "value3")
        self.assertEquals(m.value("name2"), "value2")
        self.assertEquals(m.value("name1"), "value1")
        self.assertTrue(m.value("name4") is None)

class TestMediaset(Test):

    media_class = MediaInfo
    synthesis_path = None

    def get_media(self, name="test"):
        config = MediasysConfig()
        m = self.media_class(name)
        return m

    def get_mediaset(self):
        m0 = self.get_media("m0")
        m1 = self.get_media("m1")
        m2 = self.get_media("m2")
        mediaset = Mediaset([m0, m1, m2])
        return mediaset

    def test_medias(self):
        mediaset = self.get_mediaset()
        self.assertEquals(len(mediaset.medias()), 3)

    def test_by_tag(self):
        m0 = self.get_media("m0")
        m0.set_tag("release")
        m1 = self.get_media("m1")
        m1.set_tag("release")
        m2 = self.get_media("m2")
        m2.set_tag("testing")
        mediaset = Mediaset([m0, m1, m2])
        release = mediaset.bytag("release")
        testing = mediaset.bytag("testing")
        self.assertEquals(len(release), 2)
        self.assertTrue(m0 in release)
        self.assertEquals(len(testing), 1)
        self.assertTrue(m2 in testing)

class TestURPMIMedia(Test):

    media_class = URPMIMedia

    def get_media(self):
        distroconf = MediasysConfig().get_any_distro()
        m = self.media_class(self.testrepomainrelease_dir, distroconf)
        return m

    def test_packages_by_source(self):
        m = self.get_media()
        m.load()
        found = list(m.packages_by_source("null-a"))
        self.assertEquals(len(found), 1)
        src = found[0].source()
        self.assertEquals(src.name, "null-a")
        self.assertEquals(src.fullversion, "1:2.1-72.i586")
        pkgs = list(found[0].packages())
        self.assertEquals(len(pkgs), 5)
        self.assertTrue("null-a-bummy-2.1-72.i586" in pkgs)
        self.assertTrue("null-a-dummy-2.1-72.i586" in pkgs)
        self.assertTrue("null-a-gummy-2.1-72.i586" in pkgs)
        self.assertTrue("null-a-debug-2.1-72.i586" in pkgs)

    def test_package_path(self):
        m = self.get_media()
        m.load()
        found = list(m.packages_by_source("null-a"))
        pkgs = list(found[0].packages())
        pkgs.sort()
        self.assertEquals(m.package_path(pkgs[0]),
            join(self.testrepomainrelease_dir,
                "null-a-2.1-72.i586.rpm"))
        self.assertEquals(m.package_path(pkgs[1]),
            join(self.testrepomainrelease_dir,
                "null-a-bummy-2.1-72.i586.rpm"))
        self.assertEquals(m.package_path(pkgs[2]),
            join(self.testrepomainrelease_dir,
                "null-a-debug-2.1-72.i586.rpm"))
        self.assertEquals(m.package_path(pkgs[3]),
            join(self.testrepomainrelease_dir,
                "null-a-dummy-2.1-72.i586.rpm"))
        self.assertEquals(m.package_path(pkgs[4]),
            join(self.testrepomainrelease_dir,
                "null-a-gummy-2.1-72.i586.rpm"))

class TestPush(Test):

    def test_package_push(self):
        pass
        
if __name__ == "__main__":
    import unittest
    unittest.main()
