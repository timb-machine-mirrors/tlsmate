# -*- coding: utf-8 -*-
"""Module defining various structures
"""
import collections

SessionStateId = collections.namedtuple(
    "SessionStateId", ["session_id", "cipher_suite", "version", "master_secret"]
)

SessionStateTicket = collections.namedtuple(
    "SessionStateTicket",
    ["ticket", "lifetime_hint", "cipher_suite", "version", "master_secret"],
)


Cipher = collections.namedtuple(
    "Cipher", "cipher_primitive cipher_algo cipher_type enc_key_len block_size iv_len"
)

Mac = collections.namedtuple("Mac", "hash_algo mac_len mac_key_len hmac_algo")

SymmetricKeys = collections.namedtuple("SymmetricKeys", "mac enc iv")

KeyExchangeAlgo = collections.namedtuple("KeyExchangeAlgo", "cls")


StateUpdateParams = collections.namedtuple(
    "StateUpdateParams",
    [
        "cipher_primitive",  # tls.CipherPrimitive
        "cipher_algo",
        "cipher_type",  # tls.CipherType
        "block_size",
        "enc_key",
        "mac_key",
        "iv_value",
        "iv_len",
        "mac_len",
        "hash_algo",
        "compression_method",  # tls.CompressionMethod
        "encrypt_then_mac",
        "implicit_iv",
    ],
)

StateUpdateParams2 = collections.namedtuple(
    "StateUpdateParams2",
    [
        "cipher",
        "mac",
        "keys",
        "compr",
        "enc_then_mac",
        "implicit_iv"
    ]
)


CipherSuite = collections.namedtuple("CipherSuite", "key_ex cipher mac")

MessageBlock = collections.namedtuple("MessageBlock", "content_type version fragment")


Groups = collections.namedtuple("Groups", "curve_algo")
SPCipherSuite = collections.namedtuple("SPCipherSuite", "cipher_suite cert_chain_id")

KeyExchange = collections.namedtuple("KeyExchange", "key_ex_type key_auth")

KeyShareEntry = collections.namedtuple("KeyShareEntry", "group key_exchange")

DHNumbers = collections.namedtuple("DHNumbers", "g_val p_val")
