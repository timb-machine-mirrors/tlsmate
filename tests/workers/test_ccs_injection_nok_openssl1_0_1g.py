# -*- coding: utf-8 -*-
"""Implements a class to be used for unit testing.
"""
import pathlib
from tlsmate.workers.ccs_injection import ScanCcsInjection
from tlsmate.tlssuite import TlsSuiteTester
from tlsmate.tlssuite import OpensslVersion


class TestCaseVulnerable(TlsSuiteTester):
    """Class used for tests with pytest.

    For more information refer to the documentation of the TcRecorder class.
    """

    sp_in_yaml = "profile_sig_algos_openssl1_0_2"
    recorder_yaml = "recorder_ccs_injection_nok_openssl1_0_1g"
    path = pathlib.Path(__file__)
    server_cmd = (
        "utils/start_openssl --prefix {prefix} --port {port} --cert rsa --cert2 ecdsa "
        "--mode www --ccs-inject -- -cipher ALL"
    )
    openssl_version = OpensslVersion.v1_0_1g

    server = "localhost"

    def run(self, tlsmate, is_replaying):
        server_profile = tlsmate.server_profile
        ScanCcsInjection(tlsmate).run()
        profile = server_profile.make_serializable()
        assert profile["vulnerabilities"]["ccs_injection"] == "C_TRUE"


if __name__ == "__main__":
    TestCaseVulnerable().entry(is_replaying=False)