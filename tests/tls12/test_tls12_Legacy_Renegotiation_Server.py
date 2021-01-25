# -*- coding: utf-8 -*-
"""Implements a class to be used for unit testing.
"""
import pathlib
import logging
from tests.cipher_suite_tester import CipherSuiteTester
import tlsmate.constants as tls
import tlsmate.messages as msg


class TestCase(CipherSuiteTester):
    """Class used for tests with pytest.

    For more information refer to the documentation of the CipherSuiteTester class.
    """

    name = "Legacy_Renegotiation_Server"
    path = pathlib.Path(__file__)

    # Uncomment the line below if you do not want to use the default version and
    # adapt it to your needs.
    # version = tls.Version.TLS12

    def run(self, container, is_replaying=False):
        client = container.client()

        client.versions = [tls.Version.TLS12]
        client.cipher_suites = [tls.CipherSuite.TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384]
        client.support_supported_groups = True
        client.support_signature_algorithms = True
        client.supported_groups = [
            tls.SupportedGroups.SECP256R1,
            tls.SupportedGroups.SECP384R1,
            tls.SupportedGroups.SECP521R1,
        ]
        client.signature_algorithms = [tls.SignatureScheme.RSA_PKCS1_SHA256]
        end_of_tc_reached = False
        with client.create_connection() as conn:
            conn.handshake()
            conn.wait(msg.HelloRequest)
            conn.handshake()
            end_of_tc_reached = True
        assert end_of_tc_reached is True


if __name__ == "__main__":
    TestCase().entry(is_replaying=False)