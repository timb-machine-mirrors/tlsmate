# -*- coding: utf-8 -*-
"""Implements a class to be used for unit testing.
"""
import pathlib
from tests.cipher_suite_tester import CipherSuiteTester
import tlsclient.constants as tls


class TestCase(CipherSuiteTester):
    """Class used for tests with pytest.

    For more information refer to the documentation of the CipherSuiteTester class.
    """

    path = pathlib.Path(__file__)

    cipher_suite = tls.CipherSuite.TLS_ECDHE_ECDSA_WITH_AES_128_CCM_8

    # Uncomment the line below if you do not want to use the default version and
    # adapt it to your needs.
    # version = tls.Version.TLS12


if __name__ == "__main__":
    TestCase().entry(is_replaying=False)