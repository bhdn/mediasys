from tests import Test

from mediasys.facade import MediasysFacade
from mediasys.config import Config

# so far, all path names are invalid, just to allow reading it

class TestMediasysFacadeFacade(object):

    def test_create_instance(self):
        config = Config()
        msys = MediasysFacade(config)

    def test_push_package_set(self):
        """Should accept a directory structed formed of RPMS/arches and
        allow distributing it over a set of packages
        """
        config = Config()
        msys = MediasysFacade(config)
        # with explicit target media:
        msys.add_package_set(topdir="/tmp/@6666:repsys-1.6-1/",
                distro="2010.2", media="main/updates")
        # without explicit target, let it find out which one to use
        msys.add_package_set(topdir="/tmp/@6666:repsys-1.6-1/",
                distro="cooker")

    def test_push_package_set_new_pkg(self):
        """Should notify someone about new packages pushed into the
        repository, verify permissions"""
        raise NotImplementedError

    def test_move_srpm(self):
        config = Config()
        msys = MediasysFacade(config)
        # move all children from a given SRPM
        msys.move_srpm_and_children(distro="cooker", srpm="repsys",
                from_="main/release", to="contrib/release")

    def test_remove_srpm_and_children(self):
        config = Config()
        msys = MediasysFacade(config)
        msys.remove_srpm_and_children(distro="cooker", srpm="repsys",
                media="main/testing")
