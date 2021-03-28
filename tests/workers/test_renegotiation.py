# -*- coding: utf-8 -*-
"""Implements a class to test the encrypt_then_mac worker.
"""
import pathlib
from tlsmate.workers.renegotiation import ScanRenegotiation
from tlsmate.tlssuite import TlsSuiteTester
from tlsmate.tlssuite import OpensslVersion


class TestCase(TlsSuiteTester):
    """Class used for tests with pytest.

    For more information refer to the documentation of the TcRecorder class.
    """

    sp_in_yaml = "profile_sig_algos_openssl1_0_2"
    recorder_yaml = "recorder_renegotiation"
    path = pathlib.Path(__file__)
    server_cmd = (
        "utils/start_openssl --prefix {prefix} --port {port} --cert rsa --cert2 ecdsa "
        "--mode www -- -cipher ALL"
    )
    openssl_version = OpensslVersion.v1_1_1

    server = "localhost"

    def run(self, tlsmate, is_replaying):
        server_profile = tlsmate.server_profile
        ScanRenegotiation(tlsmate).run()
        profile = server_profile.make_serializable()
        assert profile["features"]["insecure_renegotiation"] == "C_FALSE"
        assert profile["features"]["scsv_renegotiation"] == "C_TRUE"
        assert profile["features"]["secure_renegotation"] == "C_TRUE"


if __name__ == "__main__":
    TestCase().entry(is_replaying=False)