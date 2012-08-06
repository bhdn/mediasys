import os
from unittest import TestCase
from os.path import join
import shutil

class Test(TestCase):
    
    def setUp(self):
        self.rootdir = join(os.getcwd(), "tests")
        self.sharedir = join(self.rootdir, "data/")
        self.spooldir = join(self.rootdir, "spool/")
        self.recently_removed_dir = join(self.rootdir, "recently-removed")
        self.testrepoorig_dir = join(self.sharedir, "repo")
        self.rpm5_testrepoorig_dir = join(self.sharedir, "repo-rpm5")
        self.testrepo_dir = join(self.spooldir, "repo")
        self.rpm5_testrepo_dir = join(self.spooldir, "repo-rpm5")
        self.archfoo_dir = join(self.spooldir, self.testrepo_dir, "fooarch")
        self.archbar_dir = join(self.spooldir, self.testrepo_dir, "bararch")
        self.rpm5_archfoo_dir = join(self.spooldir, self.rpm5_testrepo_dir, "fooarch")
        self.rpm5_archbar_dir = join(self.spooldir, self.rpm5_testrepo_dir, "bararch")
        self.testrepomain_dir = join(self.archfoo_dir, "mAiN")
        self.rpm5_testrepomain_dir = join(self.rpm5_archfoo_dir, "mAiN")
        self.testrepomainrelease_dir = join(self.testrepomain_dir, "release")
        self.rpm5_testrepomainrelease_dir = join(self.rpm5_testrepomain_dir, "release")
        self.testrepomainrelease_synth = join(self.testrepomainrelease_dir,
                "media_info", "synthesis.hdlist.cz")
        self.testrepomainrelease_info = join(self.testrepomainrelease_dir,
                "media_info", "info.xml.lzma")
        self.rpm5_testrepomainrelease_info = join(self.rpm5_testrepomainrelease_dir,
                "media_info", "info.xml.lzma")
        self.rpm5_testrepomainrelease_synth = join(self.rpm5_testrepomainrelease_dir,
                "media_info", "synthesis.hdlist.cz")
        self.rpm5_testrepomainrelease_synth = join(self.testrepomainrelease_dir,
                "media_info", "synthesis.hdlist.cz")
        self.testrepocontrib_dir = join(self.archfoo_dir, "k0ntr1b")
        self.rpm5_testrepocontrib_dir = join(self.rpm5_archfoo_dir, "k0ntr1b")
        self.testrepocontribrelease_dir = join(self.testrepocontrib_dir,
                "release")
        self.rpm5_testrepocontribrelease_dir = join(self.rpm5_testrepocontrib_dir,
                "release")
        self.testpkgs = join(self.sharedir, "packages")
        self.testpkgnew_path = join(self.testpkgs, "null-bar-2.2-34bog2011.0.i586.rpm")
        self.testrecentlyremoved_dir = join(self.spooldir, "recently-removed")

        os.makedirs(self.spooldir)
        shutil.copytree(self.testrepoorig_dir, self.testrepo_dir)

    def test_config(self):
        from mediasys.config import MediasysConfig 
        config = MediasysConfig()
        return config.get_any_distro()

    def tearDown(self):
        shutil.rmtree(self.spooldir)
