# -*- coding: utf-8 -*-
"""Module containing the class for the configuration
"""
# import basic stuff
import os
import logging
from pathlib import Path

# import own stuff

# import other stuff
import configparser


def _str_to_bool(string):
    return string.lower() not in ["0", "off", "no", "false"]


def _str_to_strlist(string):
    return [val.strip() for val in string.split(",")]


def _str_to_int(string):
    return int(string)


def _absolute_path(path, base_path):
    if not path.startswith("/"):
        path = str(base_path / path)
    return path


class Configuration(object):
    """Class representing the configuration for tlsmate.

    The configuration is taken from the following sources (the list is ordered
    according to the priority, first item has the least priority):

    * The hard coded default values
    * The file .tlsmate.ini in the user's home directory
    * Environment variables
    * From the ini file as specified on the command line interface
    * From the command line interface parameters

    Example:
        Specifying the logging option:

        Via command line:
            tlsmate --logging=debug ...

        Via Enviroment variable:
            export TLSMATE_LOGGING=debug

        Via ini-file:

        [tlsmate]
        logging = debug

    The configuration options can be retrieved by using the object like a dict:

    >>> config = Configuration()
    >>> config["endpoint"]
    'localhost'
    """

    _format_option = {
        "progress": _str_to_bool,
        "ca_certs": _str_to_strlist,
        "client_key": _str_to_strlist,
        "client_chain": _str_to_strlist,
        "sslv2": _str_to_bool,
        "sslv3": _str_to_bool,
        "tls10": _str_to_bool,
        "tls11": _str_to_bool,
        "tls12": _str_to_bool,
        "tls13": _str_to_bool,
        "pytest_port": _str_to_int,
    }

    def __init__(self, ini_file=None, init_from_external=True):
        self.config = {
            "endpoint": "localhost",
            "logging": "error",
            "progress": False,
            "ca_certs": None,
            "client_key": None,
            "client_chain": None,
            "sslv2": False,
            "sslv3": False,
            "tls10": False,
            "tls11": False,
            "tls12": False,
            "tls13": False,
            "json": False,
            "write_profile": None,
            "read_profile": None,
            "pytest_recorder_file": None,
            "pytest_recorder_replaying": None,
            "pytest_port": None,
            "pytest_openssl_1_0_2": None,
            "pytest_openssl_1_1_1": None,
            "pytest_openssl_3_0_0": None,
        }
        parser = configparser.ConfigParser()
        if ini_file is not None:
            logging.debug(f"using config file {ini_file}")
            abs_path = Path(ini_file)
            if not abs_path.is_absolute():
                abs_path = Path.cwd() / abs_path

            if not abs_path.is_file():
                raise FileNotFoundError(abs_path)

        elif init_from_external:
            abs_path = Path.home() / ".tlsmate.ini"

        else:
            abs_path = None

        config = {}
        if abs_path:
            parser.read(str(abs_path))
            if parser.has_section("tlsmate"):
                config = parser["tlsmate"]

        for option in self.config.keys():
            val = None
            if init_from_external:
                val = os.environ.get("TLSMATE_" + option.upper())

            if val is None:
                val = config.get(option)

            if val is not None:
                func = self._format_option.get(option)
                if func is not None:
                    val = func(val)

                self.config[option] = val

        if abs_path:
            abs_dir = abs_path.parent
            for conf_item in ["ca_certs", "client_key", "client_chain"]:
                item = self.config.get(conf_item)
                if item is not None:
                    item = self.config[conf_item]
                    if isinstance(item, list):
                        item = [_absolute_path(x, abs_dir) for x in item]

                    else:
                        item = _absolute_path(item, abs_dir)

                    self.config[conf_item] = item

    def __getitem__(self, key):
        return self.config.get(key)

    def set_config(self, key, val):
        """Add a configuration option.

        If the given configuration is already defined, it will be overwritten by
        the given input.

        Arguments:
            key (str): the name of the option
            val: the value of the option
        """
        if val is not None:
            self.config[key] = val
