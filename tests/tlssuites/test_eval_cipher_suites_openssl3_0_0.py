# -*- coding: utf-8 -*-
"""Implements a class to be used for unit testing.
"""
import pathlib
from tlsmate.tlssuites.eval_cipher_suites import ScanCipherSuites
from tlsmate.tlssuite import TlsSuiteTester


tls12_cs = [
    "TLS_RSA_WITH_AES_128_CBC_SHA",
    "TLS_DHE_RSA_WITH_AES_128_CBC_SHA",
    "TLS_RSA_WITH_AES_256_CBC_SHA",
    "TLS_DHE_RSA_WITH_AES_256_CBC_SHA",
    "TLS_RSA_WITH_AES_128_CBC_SHA256",
    "TLS_RSA_WITH_AES_256_CBC_SHA256",
    "TLS_RSA_WITH_CAMELLIA_128_CBC_SHA",
    "TLS_DHE_RSA_WITH_CAMELLIA_128_CBC_SHA",
    "TLS_DHE_RSA_WITH_AES_128_CBC_SHA256",
    "TLS_DHE_RSA_WITH_AES_256_CBC_SHA256",
    "TLS_RSA_WITH_CAMELLIA_256_CBC_SHA",
    "TLS_DHE_RSA_WITH_CAMELLIA_256_CBC_SHA",
    "TLS_RSA_WITH_AES_128_GCM_SHA256",
    "TLS_RSA_WITH_AES_256_GCM_SHA384",
    "TLS_DHE_RSA_WITH_AES_128_GCM_SHA256",
    "TLS_DHE_RSA_WITH_AES_256_GCM_SHA384",
    "TLS_RSA_WITH_CAMELLIA_128_CBC_SHA256",
    "TLS_DHE_RSA_WITH_CAMELLIA_128_CBC_SHA256",
    "TLS_RSA_WITH_CAMELLIA_256_CBC_SHA256",
    "TLS_DHE_RSA_WITH_CAMELLIA_256_CBC_SHA256",
    "TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA",
    "TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA",
    "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA",
    "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA",
    "TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA256",
    "TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA384",
    "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA256",
    "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA384",
    "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
    "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
    "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
    "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
    "TLS_RSA_WITH_ARIA_128_GCM_SHA256",
    "TLS_RSA_WITH_ARIA_256_GCM_SHA384",
    "TLS_DHE_RSA_WITH_ARIA_128_GCM_SHA256",
    "TLS_DHE_RSA_WITH_ARIA_256_GCM_SHA384",
    "TLS_ECDHE_ECDSA_WITH_ARIA_128_GCM_SHA256",
    "TLS_ECDHE_ECDSA_WITH_ARIA_256_GCM_SHA384",
    "TLS_ECDHE_RSA_WITH_ARIA_128_GCM_SHA256",
    "TLS_ECDHE_RSA_WITH_ARIA_256_GCM_SHA384",
    "TLS_ECDHE_ECDSA_WITH_CAMELLIA_128_CBC_SHA256",
    "TLS_ECDHE_ECDSA_WITH_CAMELLIA_256_CBC_SHA384",
    "TLS_ECDHE_RSA_WITH_CAMELLIA_128_CBC_SHA256",
    "TLS_ECDHE_RSA_WITH_CAMELLIA_256_CBC_SHA384",
    "TLS_RSA_WITH_AES_128_CCM",
    "TLS_RSA_WITH_AES_256_CCM",
    "TLS_DHE_RSA_WITH_AES_128_CCM",
    "TLS_DHE_RSA_WITH_AES_256_CCM",
    "TLS_RSA_WITH_AES_128_CCM_8",
    "TLS_RSA_WITH_AES_256_CCM_8",
    "TLS_DHE_RSA_WITH_AES_128_CCM_8",
    "TLS_DHE_RSA_WITH_AES_256_CCM_8",
    "TLS_ECDHE_ECDSA_WITH_AES_128_CCM",
    "TLS_ECDHE_ECDSA_WITH_AES_256_CCM",
    "TLS_ECDHE_ECDSA_WITH_AES_128_CCM_8",
    "TLS_ECDHE_ECDSA_WITH_AES_256_CCM_8",
    "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256",
    "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256",
    "TLS_DHE_RSA_WITH_CHACHA20_POLY1305_SHA256",
]

tls13_cs = [
    "TLS_AES_128_GCM_SHA256",
    "TLS_AES_256_GCM_SHA384",
    "TLS_CHACHA20_POLY1305_SHA256",
]


class TestCase(TlsSuiteTester):
    """Class used for tests with pytest.

    For more information refer to the documentation of the TcRecorder class.
    """

    sp_out_yaml = "profile_basic_openssl3_0_0"
    recorder_yaml = "recorder_eval_cipher_suites_openssl3_0_0"
    path = pathlib.Path(__file__)

    server = "localhost"
    port = 44332

    def check_cert_chain(self, cert_chain):
        assert len(cert_chain) == 2
        assert cert_chain[0]["id"] == 1
        assert cert_chain[1]["id"] == 2
        assert len(cert_chain[0]["cert_chain"]) == 3
        assert len(cert_chain[1]["cert_chain"]) == 3

    def check_versions(self, versions):
        assert len(versions) == 2
        assert versions[0]["version"]["name"] == "TLS12"
        assert versions[0]["server_preference"] == "C_FALSE"
        assert versions[1]["version"]["name"] == "TLS13"
        assert versions[1]["server_preference"] == "C_FALSE"
        for a, b in zip(tls12_cs, versions[0]["cipher_suites"]):
            assert a == b["name"]
        for a, b in zip(tls13_cs, versions[1]["cipher_suites"]):
            assert a == b["name"]

    def check_profile(self, profile):
        self.check_cert_chain(profile["cert_chains"])
        self.check_versions(profile["versions"])

    def run(self, container, is_replaying):
        server_profile = container.server_profile()
        test_suite = ScanCipherSuites()
        test_suite._inject_dependencies(server_profile, container.client())
        test_suite.run()

        self.check_profile(server_profile.make_serializable())


if __name__ == "__main__":
    TestCase().entry(is_replaying=False)
