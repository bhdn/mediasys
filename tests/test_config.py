from tests import Test

import mediasys.config

class ConfigTest(Test):

    def test_create_instance(self):
        config = mediasys.config.Config()
