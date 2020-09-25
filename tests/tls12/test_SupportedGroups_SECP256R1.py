# -*- coding: utf-8 -*-
"""Implements a class to be used for unit testing.
"""
import pytest
import pathlib
from tests.tc_recorder import TcRecorder
import tlsclient.constants as tls


class TestCase(TcRecorder):
    """Class used for tests with pytest.

    For more information refer to the documentation of the TcRecorder class.
    """

    name = "SupportedGroups_SECP256R1"
    path = pathlib.Path(__file__)

    cipher_suite = tls.CipherSuite.TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA256

    # Uncomment the line below if you do not want to use the default version and
    # adapt it to your needs.
    # version = tls.Version.TLS12

    supported_groups = [tls.SupportedGroups.SECP256R1]

if __name__ == "__main__":
    TestCase().record_testcase()