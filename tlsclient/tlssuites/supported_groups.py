# -*- coding: utf-8 -*-
"""Module containing the test suite
"""
import logging
import abc
import tlsclient.messages as msg
import tlsclient.constants as tls
from tlsclient.tlssuite import TlsSuite
from tlsclient.exception import ScanError
from tlsclient.server_profile import ProfileEnum, ProfileBasicEnum
from tlsclient import utils
from tlsclient.exception import CurveNotSupportedError


class _Scan(metaclass=abc.ABCMeta):
    def __init__(self, vers_prof, version, testsuite):
        self._version = version
        self._client = testsuite.client
        self._version_prof = vers_prof
        self._profile_groups = (
            testsuite.server_profile.get("versions")
            .key(version)
            .get("supported_groups")
        )

    @abc.abstractmethod
    def _get_cipher_suites(self):
        raise NotImplementedError

    @abc.abstractmethod
    def _get_group_from_server(self, offered_groups):
        raise NotImplementedError

    def _determine_supported_groups(self):
        offered_groups = self._offered_groups[:]
        supported_groups = []
        max_items = 20
        while offered_groups:
            sub_set = offered_groups[:max_items]
            offered_groups = offered_groups[max_items:]
            while sub_set:
                server_group = self._get_group_from_server(sub_set)
                if server_group is None:
                    break
                self._profile_groups.get("groups").append(ProfileEnum(server_group))
                if server_group not in sub_set:
                    self._profile_groups.get("extension_supported").set(
                        tls.SPBool.C_FALSE
                    )
                    return
                supported_groups.append(server_group)
                sub_set.remove(server_group)
        if not supported_groups:
            raise ScanError("ECDHE cipher suites negotiated, but no groups supported")
        self._profile_groups.get("extension_supported").set(tls.SPBool.C_TRUE)
        self.groups = supported_groups

    def _determine_server_preference(self):
        status = None
        if len(self.groups) > 1:
            ref_group = self.groups[0]
            self.groups.append(self.groups.pop(0))
            server_group = self._get_group_from_server(self.groups)
            self.groups.insert(0, self.groups.pop())
            if server_group is not None:
                if server_group is ref_group:
                    status = tls.SPBool.C_TRUE
                else:
                    status = tls.SPBool.C_FALSE
        else:
            status = tls.SPBool.C_NA
        if status is not None:
            self._profile_groups.add("server_preference", ProfileBasicEnum(status))

    @abc.abstractmethod
    def _determine_advertised_group(self):
        raise NotImplementedError

    def scan(self, testsuite_name):
        try:
            self._client.cipher_suites = self._get_cipher_suites()
            if not self._client.cipher_suites:
                raise ScanError("No (EC)DH cipher suites supported")
            self._client.versions = [self._version]
            self._client.signature_algorithms = [
                tls.SignatureScheme.ED25519,
                tls.SignatureScheme.ED448,
                tls.SignatureScheme.ECDSA_SECP384R1_SHA384,
                tls.SignatureScheme.ECDSA_SECP256R1_SHA256,
                tls.SignatureScheme.ECDSA_SECP521R1_SHA512,
                tls.SignatureScheme.RSA_PSS_RSAE_SHA256,
                tls.SignatureScheme.RSA_PSS_RSAE_SHA384,
                tls.SignatureScheme.RSA_PSS_RSAE_SHA512,
                tls.SignatureScheme.RSA_PKCS1_SHA256,
                tls.SignatureScheme.RSA_PKCS1_SHA384,
                tls.SignatureScheme.RSA_PKCS1_SHA512,
                tls.SignatureScheme.ECDSA_SHA1,
                tls.SignatureScheme.RSA_PKCS1_SHA1,
            ]
            self._determine_supported_groups()
            if (
                self._profile_groups.get("extension_supported").get()
                is tls.SPBool.C_TRUE
            ):
                self._determine_server_preference()
                self._determine_advertised_group()
        except ScanError as exc:
            logging.info(f'scan error in "{testsuite_name}": {exc.message}')
            # TODO: strategy for handling status messages
            self._profile_groups.set_status(exc.message)


class _TLS12_Scan(_Scan):

    _offered_groups = tls.SupportedGroups.all()

    def _get_cipher_suites(self):
        cipher_suites = self._version_prof.get("cipher_suites").all()
        return utils.filter_cipher_suites(
            cipher_suites,
            key_algo=[
                tls.KeyExchangeAlgorithm.ECDHE_ECDSA,
                tls.KeyExchangeAlgorithm.ECDHE_RSA,
            ],
        )

    def _get_group_from_server(self, offered_groups):
        self._client.support_supported_groups = True
        self._client.supported_groups = offered_groups
        with self._client.create_connection() as conn:
            conn.send(msg.ClientHello)
            conn.wait(msg.ServerHello)
            conn.wait(msg.Certificate, optional=True)
            try:
                msg_ske = conn.wait(msg.ServerKeyExchange)
            except CurveNotSupportedError as exc:
                return exc.curve
            if msg_ske is None or msg_ske.ec is None:
                return None
            return msg_ske.ec.named_curve
        return None

    def _determine_advertised_group(self):
        pass
        # self._profile_groups.get("groups_advertised").set(tls.SPBool.C_NA)


class _TLS13_Scan(_Scan):

    _offered_groups = [
        tls.SupportedGroups.SECP256R1,
        tls.SupportedGroups.SECP384R1,
        tls.SupportedGroups.SECP521R1,
        tls.SupportedGroups.X25519,
        tls.SupportedGroups.X448,
        tls.SupportedGroups.FFDHE2048,
        tls.SupportedGroups.FFDHE3072,
        tls.SupportedGroups.FFDHE4096,
        tls.SupportedGroups.FFDHE6144,
        tls.SupportedGroups.FFDHE8192,
    ]

    def _get_cipher_suites(self):
        return self._version_prof.get("cipher_suites").all()

    def _get_share_from_server(self, offered_groups):
        self._client.support_supported_groups = True
        self._client.supported_groups = offered_groups
        self._client.key_shares = offered_groups
        with self._client.create_connection() as conn:
            conn.send(msg.ClientHello)
            conn.wait(msg.ServerHello)
        if conn.msg.server_hello is None:
            return None
        try:
            key_share_ext = conn.msg.server_hello.get_extension(tls.Extension.KEY_SHARE)
            key_share = key_share_ext.key_shares[0]
            if key_share.group not in offered_groups:
                raise ScanError("selected group was not offered")
        except AttributeError as exc:
            raise ScanError("cannot get selected group from server_hello") from exc
        return key_share

    def _get_group_from_server(self, offered_groups):
        share = self._get_share_from_server(offered_groups)
        if share is not None:
            return share.group
        return None

    def _determine_advertised_group(self):
        status = None
        self._client.supported_groups = self.groups[:1]
        self._client.key_shares = self.groups[:1]
        encrypted_extensions = None
        with self._client.create_connection() as conn:
            conn.send(msg.ClientHello)
            conn.wait(msg.ServerHello)
            conn.wait(msg.ChangeCipherSpec, optional=True)
            encrypted_extensions = conn.wait(msg.EncryptedExtensions)
        if encrypted_extensions is not None:
            supported_group_ext = encrypted_extensions.get_extension(
                tls.Extension.SUPPORTED_GROUPS
            )
            if supported_group_ext is None:
                status = tls.SPBool.C_FALSE
            else:
                advertised_groups = supported_group_ext.supported_groups
                self.groups = advertised_groups
                status = tls.SPBool.C_TRUE
                if (
                    self._profile_groups.get("server_preference")
                    is not tls.SPBool.C_TRUE
                ):
                    if set(advertised_groups) != set(self.groups):
                        raise ScanError(
                            "server's advertised groups differ from accepted groups"
                        )
        if status is not None:
            self._profile_groups.add("groups_advertised", ProfileBasicEnum(status))


class ScanSupportedGroups(TlsSuite):
    name = "groups"
    descr = "check for FF-DH and EC groups"
    prio = 20

    def run(self):

        versions = self.server_profile.get("versions").all()
        if tls.Version.SSL20 in versions:
            versions.remove(tls.Version.SSL20)
        for version in versions:
            vers_prof = self.server_profile.get("versions").key(version)
            if vers_prof is not None:
                if version is tls.Version.TLS13:
                    cls = _TLS13_Scan
                else:
                    cls = _TLS12_Scan
                cls(vers_prof, version, self).scan(self.name)