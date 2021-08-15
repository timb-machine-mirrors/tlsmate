# -*- coding: utf-8 -*-
"""Module for OCSP stapling worker
"""
# import basic stuff

# import own stuff
from tlsmate import tls
from tlsmate.plugin import WorkerPlugin

# import other stuff

class ScanOcspStapling(WorkerPlugin):
    name = "ocsp_stapling"
    descr = "scan for OCSP stapling"
    prio = 30

    def _scan_stapling(self):

        versions = tls.Version.tls_only()
        prof_values = self.server_profile.get_profile_values(versions, full_hs=True)
        if not prof_values.versions:
            status = tls.SPBool.C_NA

        else:
            self.client.init_profile(profile_values=prof_values)
            self.client.alert_on_invalid_cert = False
            self.client.profile.support_status_request = True
            with self.client.create_connection() as conn:
                conn.handshake()

            # Hm, some TLS libraries return the status_request(_v2) extension in the
            # server_hello, and some are not (e.g. openssl for TLS13). So check if
            # OCSP status request is received without evaluating it. Evaluating
            # the responses would require more sophisticated handling, as the state
            # should then be determined for all certificate chains, repectively
            # for all certificates (status_request_v2) for which a response is
            # received.

            if not conn.handshake_completed:
                status = tls.SPBool.C_UNDETERMINED

            elif conn.stapling_status:
                status = tls.SPBool.C_TRUE

            else:
                status = tls.SPBool.C_FALSE

        self.server_profile.features.ocsp_stapling = status

    def _scan_multi_stapling(self):

        prof_values = self.server_profile.get_profile_values(
            [tls.Version.TLS10, tls.Version.TLS11, tls.Version.TLS12], full_hs=True
        )
        if not prof_values.versions:
            status = tls.SPBool.C_NA

        else:
            self.client.init_profile(profile_values=prof_values)
            self.client.alert_on_invalid_cert = False
            self.client.profile.support_status_request_v2 = tls.StatusType.OCSP_MULTI
            with self.client.create_connection() as conn:
                conn.handshake()

            if conn.msg.server_hello is None:
                status = tls.SPBool.C_UNDETERMINED

            elif conn.msg.server_hello.get_extension(tls.Extension.STATUS_REQUEST_V2):
                status = tls.SPBool.C_TRUE

            else:
                status = tls.SPBool.C_FALSE

        self.server_profile.features.ocsp_multi_stapling = status

    def run(self):

        self._scan_stapling()
        self._scan_multi_stapling()
