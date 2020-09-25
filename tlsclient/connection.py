# -*- coding: utf-8 -*-
"""Module containing the class implementing a TLS connection
"""

import os
import time
import select
import inspect
import logging

from tlsclient.protocol import ProtocolData
from tlsclient.alert import FatalAlert
import tlsclient.constants as tls
from tlsclient.messages import (
    Alert,
    HandshakeMessage,
    ChangeCipherSpecMessage,
    AppDataMessage,
)
from tlsclient.key_exchange import RsaKeyExchange, DhKeyExchange, EcdhKeyExchange


from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography import x509

class TlsConnectionMsgs(object):

    map_msg2attr = {
        tls.HandshakeType.HELLO_REQUEST: None,
        tls.HandshakeType.CLIENT_HELLO: None,
        tls.HandshakeType.SERVER_HELLO: "server_hello",
        tls.HandshakeType.NEW_SESSION_TICKET: None,
        tls.HandshakeType.END_OF_EARLY_DATA: None,
        tls.HandshakeType.ENCRYPTED_EXTENSIONS: None,
        tls.HandshakeType.CERTIFICATE: "server_certificate",
        tls.HandshakeType.SERVER_KEY_EXCHANGE: "server_key_exchange",
        tls.HandshakeType.CERTIFICATE_REQUEST: None,
        tls.HandshakeType.SERVER_HELLO_DONE: "server_hello_done",
        tls.HandshakeType.CERTIFICATE_VERIFY: None,
        tls.HandshakeType.CLIENT_KEY_EXCHANGE: None,
        tls.HandshakeType.FINISHED: "server_finished",
        tls.HandshakeType.KEY_UPDATE: None,
        tls.HandshakeType.COMPRESSED_CERTIFICATE: None,
        tls.HandshakeType.EKT_KEY: None,
        tls.HandshakeType.MESSAGE_HASH: None,
    }

    def __init__(self):
        self.client_hello = None
        self.server_hello = None
        self.server_certificate = None
        self.server_key_exchange = None
        self.server_hello_done = None
        self.client_certificate = None
        self.client_key_exchange = None
        self.client_change_cipher_spec = None
        self.client_finished = None
        self.server_change_cipher_spec = None
        self.server_finished = None
        self.client_alert = None
        self.server_alert = None

    def store_received_msg(self, msg):
        if msg.content_type == tls.ContentType.HANDSHAKE:
            attr = self.map_msg2attr.get(msg.msg_type, None)
            if attr is not None:
                setattr(self, attr, msg)
        elif msg.content_type == tls.ContentType.CHANGE_CIPHER_SPEC:
            self.server_change_cipher_spec = msg
        elif msg.content_type == tls.ContentType.ALERT:
            self.server_alert = msg


class TlsConnection(object):
    def __init__(
        self,
        connection_msgs,
        security_parameters,
        record_layer,
        recorder,
    ):
        self.msg = connection_msgs
        self.received_data = ProtocolData()
        self.queued_msg = None
        self.record_layer = record_layer
        self.sec_param = security_parameters
        self.record_layer_version = tls.Version.TLS10
        self._update_write_state = False
        self._msg_hash = None
        self._msg_hash_queue = None
        self._msg_hash_active = False
        self.recorder = recorder

    def __enter__(self):
        logging.debug("New TLS connection created")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is FatalAlert:
            self.send(
                Alert(level=tls.AlertLevel.FATAL, description=exc_value.description)
            )
            self.record_layer.close_socket()
            return True
        self.record_layer.close_socket()
        logging.debug("TLS connection closed")
        return False

    def set_recorder(self, recorder):
        self.recorder = recorder
        self.sec_param.set_recorder(recorder)
        self.record_layer.set_recorder(recorder)

    def set_profile(self, client_profile):
        self.client_profile = client_profile
        return self

    def rsa_key_transport(self):
        binary_cert = self.msg.server_certificate.certificates[0]
        cert = x509.load_der_x509_certificate(binary_cert)
        pub_key = cert.public_key()
        ciphered_key = pub_key.encrypt(bytes(self.sec_param.pre_master_secret), padding.PKCS1v15())
        # injecting the encrypted key to the recorder is required, as the
        # padding scheme PKCS1v15 produces non-deterministic cipher text.
        return self.recorder.inject(rsa_enciphered=ciphered_key)


    def get_extension(self, extensions, ext_id):
        for ext in extensions:
            if ext.extension_id == ext_id:
                return ext
        return None


    def server_hello_received(self, msg):
        if self.get_extension(msg.extensions, tls.Extension.ENCRYPT_THEN_MAC) is not None:
            self.sec_param.encrypt_then_mac = True

    def send(self, *messages):
        for msg in messages:
            if inspect.isclass(msg):
                msg = msg()
                msg.auto_generate_msg(self)
            msg_data = msg.serialize(self)

            self.record_layer.send_message(
                tls.MessageBlock(
                    content_type=msg.content_type,
                    version=self.record_layer_version,
                    fragment=msg_data,
                )
            )
            self._check_update_write_state()

        self.record_layer.flush()

    def wait(self, msg_class, optional=False):
        if self.queued_msg:
            msg = self.queued_msg
            self.queued_msg = None
        else:
            content_type, version, fragment = self.record_layer.wait_fragment()
            if content_type is tls.ContentType.HANDSHAKE:
                msg = HandshakeMessage.deserialize(fragment, self)
            elif content_type is tls.ContentType.ALERT:
                raise NotImplementedError("Receiving an Alert is not yet implemented")
            elif content_type is tls.ContentType.CHANGE_CIPHER_SPEC:
                msg = ChangeCipherSpecMessage.deserialize(fragment, self)
            elif content_type is tls.ContentType.APPLICATION_DATA:
                msg = AppDataMessage.deserialize(fragment, self)
            else:
                raise ValueError("Content type unknow")

        self.msg.store_received_msg(msg)

        if isinstance(msg, msg_class):
            return msg
        else:
            if optional:
                self.queued_msg = msg
                return None
            else:
                raise FatalAlert(
                    "Unexpected message received: {}, expected: {}".format(
                        type(msg), msg_class
                    ),
                    tls.AlertDescription.UNEXPECTED_MESSAGE,
                )

    def update_keys(self):
        self.sec_param.pre_master_secret = self.key_exchange.agree_on_premaster_secret()
        self.sec_param.generate_master_secret(self.msg.server_key_exchange)
        self.sec_param.key_deriviation()

    aaa = {
        tls.KeyExchangeAlgorithm.DHE_DSS : DhKeyExchange,
        tls.KeyExchangeAlgorithm.DHE_RSA : DhKeyExchange,
        tls.KeyExchangeAlgorithm.DH_ANON : None,
        tls.KeyExchangeAlgorithm.RSA : RsaKeyExchange,
        tls.KeyExchangeAlgorithm.DH_DSS : None,
        tls.KeyExchangeAlgorithm.DH_RSA : None,
        tls.KeyExchangeAlgorithm.ECDH_ECDSA : EcdhKeyExchange,
        tls.KeyExchangeAlgorithm.ECDHE_ECDSA : EcdhKeyExchange,
        tls.KeyExchangeAlgorithm.ECDH_RSA : EcdhKeyExchange,
        tls.KeyExchangeAlgorithm.ECDHE_RSA : EcdhKeyExchange,
        tls.KeyExchangeAlgorithm.EC_DIFFIE_HELLMAN : EcdhKeyExchange,
    }


    def update(self, **kwargs):
        for argname, val in kwargs.items():
            if argname == "version":
                self.version = val
                self.sec_param.version = val
                # stupid TLS1.3 RFC: let the message look like TLS1.2
                # to support not compliant middleboxes. :-(
                self.record_layer_version = min(val, tls.Version.TLS12)
            elif argname == "cipher_suite":
                self.sec_param.update_cipher_suite(val)
                key_ex_class = self.aaa[self.sec_param.key_exchange_method]
                self.key_exchange = key_ex_class(self, self.recorder)
            elif argname == "server_random":
                self.sec_param.server_random = val
            elif argname == "client_random":
                self.sec_param.client_random = val
            elif argname == "named_curve":
                self.sec_param.named_curve = val
            elif argname == "remote_public_key":
                self.sec_param.remote_public_key = val
            elif argname == "client_version_sent":
                self.client_version_sent = val
            elif argname == "server_hello":
                self.server_hello_received(val)
            else:
                raise ValueError(
                    'Update connection: unknown argument "{}" given'.format(argname)
                )

    def _check_update_write_state(self):
        if self._update_write_state:
            state = self.sec_param.get_pending_write_state(self.sec_param.entity)
            self.record_layer.update_write_state(state)
            self._update_write_state = False

    def update_write_state(self):
        self._update_write_state = True

    def update_read_state(self):
        if self.sec_param.entity == tls.Entity.CLIENT:
            entity = tls.Entity.SERVER
        else:
            entity = tls.Entity.CLIENT
        state = self.sec_param.get_pending_write_state(entity)
        self.record_layer.update_read_state(state)

    def init_msg_hash(self):
        self._msg_hash_queue = ProtocolData()
        self._msg_hash = None
        self._msg_hash_active = True

        self._debug = []

    def update_msg_hash(self, msg):
        self._debug.append(msg)
        if not self._msg_hash_active:
            return
        if self.sec_param.hash_algo is None:
            # cipher suite not yet negotiated, no hash algo available yet
            self._msg_hash_queue.extend(msg)
        else:
            if self._msg_hash is None:
                self._msg_hash = hashes.Hash(self.sec_param.hmac_algo())
                self._msg_hash.update(self._msg_hash_queue)
                self._msg_hash_queue = None
            self._msg_hash.update(msg)

    def finalize_msg_hash(self, intermediate=False):
        if intermediate:
            hash_tmp = self._msg_hash.copy()
            return hash_tmp.finalize()
        val = self._msg_hash.finalize()
        self._msg_hash_active = False
        self._msg_hash = None
        self._msg_hash_queue = None
        return val