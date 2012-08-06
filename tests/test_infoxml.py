import os
from tests import Test
from mediasys.infoxml import InfoxmlParser, InfoxmlParseError

class TestInfoXMLParser(Test):
    
    def test_load(self):
        config = self.test_config()
        parser = InfoxmlParser(self.testrepomainrelease_dir, config)
        contents = parser.load()
        self.assertTrue({'url': 'ftp://sunsite.unc.edu/pub/Linux/libs/graphics/',
                'sourcerpm': 't1lib-5.1.2-13.src.rpm',
                'license': 'LGPLv2+',
                'fn': 't1lib-config-5.1.2-13.i586',
                'descr': """
T1lib is a library for generating character and string-glyphs from
Adobe Type 1 fonts under UNIX. T1lib uses most of the code of the X11
rasterizer donated by IBM to the X11-project. But some disadvantages
of the rasterizer being included in X11 have been eliminated.  T1lib
also includes a support for antialiasing.
"""} in contents)
        self.assertTrue({'url': '', 'sourcerpm': 'null-bar-2.1-34bog2011.0.src.rpm',
                'license': 'GPL', 'fn': 'null-bar-2.1-34bog2011.0.i586',
                'descr': '\nDummy package.\n'} in contents)
        self.assertTrue({'url': '', 'sourcerpm':
                        'etcskel-1.63-27mdv2011.0.src.rpm',
                        'license': 'Public Domain',
                        'fn': 'etcskel-1.63-27mdv2011.0.noarch',
                        'descr': """
The etcskel package is part of the basic Mandriva system.

Etcskel provides the /etc/skel directory's files. These files are then placed
in every new user's home directory when new accounts are created.
"""} in contents)
        self.assertTrue({'url': 'http://www.lxde.org',
                    'sourcerpm':
                    'mandriva-lxde-config-0.5-2mdv2010.1.src.rpm',
                    'license': 'GPLv2+', 'fn':
                    'mandriva-lxde-config-Free-0.5-2mdv2010.1.noarch',
                    'descr':
                    '\nConfiguration files for Mandriva Free LXDE desktop environment.\n'
                    } in contents)
        self.assertTrue({'url': '',
                    'sourcerpm': 'null-foo-2.1-34bog2011.0.src.rpm',
                    'license': 'GPL',
                    'fn': 'null-foo-2.1-34bog2011.0.i586',
                    'descr': '\nDummy package.\n'} in contents)

    def test_parse_error(self):
        path = "/dev/urandom"
        if not os.path.exists(path):
            self.skipTest("%s not found" % (path))
            return
        config = self.test_config()
        parser = InfoxmlParser(path, config)
        self.assertRaises(InfoxmlParseError, parser.load)

    def test_not_found(self):
        path = "./not-found"
        config = self.test_config()
        parser = InfoxmlParser(path, config)
        self.assertRaises(InfoxmlParseError, parser.load)

    def test_command_not_found(self):
        config = self.test_config()
        config.lzcat_cmd = "./not-found"
        basedir = os.path.dirname(self.testrepomainrelease_dir)
        parser = InfoxmlParser(basedir, config)
        self.assertRaises(InfoxmlParseError, parser.load)
