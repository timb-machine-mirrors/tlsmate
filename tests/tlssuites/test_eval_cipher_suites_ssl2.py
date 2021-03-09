# -*- coding: utf-8 -*-
"""Implements a class to be used for unit testing.
"""
import pathlib
from tlsmate.tlssuites.eval_cipher_suites import ScanCipherSuites
from tlsmate.tlssuite import TlsSuiteTester
from tlsmate.tlssuite import OpensslVersion

ssl2_ck = [
    "SSL_CK_RC4_128_WITH_MD5",
    "SSL_CK_RC2_128_CBC_WITH_MD5",
    "SSL_CK_IDEA_128_CBC_WITH_MD5",
    "SSL_CK_DES_192_EDE3_CBC_WITH_MD5",
]


class TestCase(TlsSuiteTester):
    """Class used for tests with pytest.

    For more information refer to the documentation of the TcRecorder class.
    """

    sp_out_yaml = "profile_basic_ssl2"
    recorder_yaml = "recorder_eval_cipher_suites_ssl2"
    path = pathlib.Path(__file__)
    server_cmd = (
        "utils/start_openssl --prefix {prefix} --port {port} --mode www --sslv2"
    )
    openssl_version = OpensslVersion.v1_0_2

    server = "localhost"

    def check_versions(self, versions):
        assert len(versions) == 1
        assert versions[0]["version"]["name"] == "SSL20"
        assert versions[0]["server_preference"] == "C_UNDETERMINED"
        for a, b in zip(ssl2_ck, versions[0]["cipher_suites"]):
            assert a == b["name"]

    def check_profile(self, profile):
        self.check_versions(profile["versions"])

    def run(self, tlsmate, is_replaying):
        server_profile = tlsmate.server_profile
        test_suite = ScanCipherSuites()
        test_suite._inject_dependencies(server_profile, tlsmate.client)
        test_suite.run()

        self.check_profile(server_profile.make_serializable())


if __name__ == "__main__":
    TestCase().entry(is_replaying=False)
