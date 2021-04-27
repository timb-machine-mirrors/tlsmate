# -*- coding: utf-8 -*-
"""Module scanning for the Heartbleet vulnerability

Refer to CVE-2014-0160, bug in openssl versions, no proper length check
for the heartbeat request. Refer to https://heartbleed.com/
"""
# import basic stuff

# import own stuff
from tlsmate import msg
from tlsmate import tls
from tlsmate.plugin import WorkerPlugin

# import other stuff


class ScanHeartbleed(WorkerPlugin):
    name = "heartbleed"
    descr = "check if server is vulnerable to Heartbleed vulnerability"
    prio = 41

    def run(self):
        hb = getattr(
            self.server_profile.features, "heartbeat", tls.SPHeartbeat.C_UNDETERMINED
        )

        state = tls.SPBool.C_UNDETERMINED
        if hb in (tls.SPHeartbeat.C_FALSE, tls.SPHeartbeat.C_NA):
            state = tls.SPBool.C_NA

        elif hb is tls.SPHeartbeat.C_TRUE:
            values = self.server_profile.get_profile_values(
                tls.Version.all(), full_hs=True
            )
            self.client.init_profile(profile_values=values)
            self.client.heartbeat_mode = tls.HeartbeatMode.PEER_ALLOWED_TO_SEND
            with self.client.create_connection() as conn:
                conn.handshake()
                request = msg.HeartbeatRequest()
                request.payload = b"abc"
                request.payload_length = 4
                request.padding = b""
                conn.send(request)
                response = conn.wait(msg.HeartbeatResponse, timeout=2000)
                if response is not None:
                    state = (
                        tls.SPBool.C_TRUE
                        if response.payload_length == 4
                        else tls.SPBool.C_FALSE
                    )

        self.server_profile.vulnerabilities.heartbleed = state