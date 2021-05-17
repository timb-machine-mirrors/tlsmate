# -*- coding: utf-8 -*-
"""Module defining classes for test suites
"""
# import basic stuff
import abc
import subprocess
import sys
import time
import enum
import os
import logging

# import own stuff
from tlsmate.tlsmate import TlsMate, TLSMATE_DIR
from tlsmate import utils
from tlsmate.config import Configuration, ConfigItem
from tlsmate.connection import TlsConnection

# import other stuff


class OpensslVersion(enum.Enum):
    """Defines the openssl versions which are used to generate the unit tests.

    Note, that the openssl versions must be build in the directory "openssl".
    E.g., the binary executable for versions 3.0.0 is located in
    openssl/openssl3_0_0/apps/openssl (base directory is the source directory
    for tlsmate.)

    Note, that the names of the enums must start with "v" followed by the version
    string that is passed to the utils/start_openssl script.
    """

    v1_0_1e = enum.auto()
    v1_0_1g = enum.auto()
    v1_0_2 = enum.auto()
    v1_1_1 = enum.auto()
    v3_0_0 = enum.auto()


class TlsSuiteTester(metaclass=abc.ABCMeta):
    """Base class to define unit tests

    Attributes:
        recorder_yaml (str): the name of the yaml file with the serialized recorder
            object
        sp_in_yaml (str): the file name of the server profile to read and deserialize
        sp_out_yaml (str): the file name of server profile to write and serialize
        path (pathlib.Path): the path of the test script
        server (str): the name of the server to use to generate the test case
        port (int): the port number to use to generate the test case
    """

    recorder_yaml = None
    sp_in_yaml = None
    sp_out_yaml = None
    path = None

    def _start_server(self):

        ca_cmd = TLSMATE_DIR / "utils/start_ca_servers"
        logging.debug(f'starting CA servers with command "{ca_cmd}"')
        exit_code = os.system(TLSMATE_DIR / "utils/start_ca_servers")
        if exit_code != 0:
            raise ValueError(f"Could not start CA servers, exit code: {exit_code}")

        cmd = (
            str(TLSMATE_DIR)
            + "/"
            + self.server_cmd.format(
                openssl_version=f'openssl{self.openssl_version.name.lstrip("v")}',
                server_port=self.config.get("server_port"),
            )
        )

        logging.debug(f'starting TLS server with command "{cmd}"')
        self.server_proc = subprocess.Popen(
            cmd.split(),
            stdin=subprocess.PIPE,
            stdout=sys.stdout,
            universal_newlines=True,
        )
        time.sleep(2)  # give openssl some time for a clean startup

    def server_input(self, input_str, timeout=None):
        """Feed a string to the server process' STDIN pipe

        Arguments:
            input_str (str): the string to provide on the STDIN pipe
            timeout (int): the timeout to wait before providing the input in
                milliseconds.
        """

        if self.recorder.is_injecting():
            return

        if timeout is not None:
            self.recorder.additional_delay(timeout / 1000)
            time.sleep(timeout / 1000)

        print(input_str, file=self.server_proc.stdin, flush=True)

    def get_yaml_file(self, name):
        """Determine the file where an object is serialized to.

        Arguments:
            name (str): the basic name of the file, without directory and without
                the suffix

        Returns:
            :class:`pathlib.Path`: a Path object for the yaml file
        """

        if name is None:
            return None

        return self.path.resolve().parent / "recordings" / (name + ".yaml")

    def _init_classes(self):
        """Init class attributes.

        Between two test cases some class attributes must be reset.
        """

        TlsConnection.reset()

    def entry(self, is_replaying=False):
        """Entry point for a test case.

        Arguments:
            is_replaying (bool): an indication if the test case is replayed or recorded.
                Defaults to False.
        """

        self._init_classes()

        if is_replaying:
            ini_file = None

        else:
            ini_file = TLSMATE_DIR / "tests/tlsmate.ini"
            if not ini_file.is_file():
                ini_file = None

        self.config = Configuration()
        self.config.register(ConfigItem("server_port", type=int, default=44330))
        self.config.register(ConfigItem("server", type=str, default="localhost"))
        self.config.register(ConfigItem("pytest_recorder_file", type=str))
        self.config.register(ConfigItem("pytest_recorder_replaying", type=str))

        if not is_replaying:
            self.config.init_from_external(ini_file)

        self.config.set(
            "endpoint", f'{self.config.get("server")}:{self.config.get("server_port")}'
        )
        self.config.set("progress", False)
        self.config.set("read_profile", self.get_yaml_file(self.sp_in_yaml))
        self.config.set("pytest_recorder_file", self.get_yaml_file(self.recorder_yaml))
        self.config.set("pytest_recorder_replaying", is_replaying)
        utils.set_logging(self.config.get("logging"))

        self.tlsmate = TlsMate(self.config)
        self.recorder = self.tlsmate.recorder

        if not is_replaying:
            if self.server_cmd is not None:
                self._start_server()

        self.run(self.tlsmate, is_replaying)

        if not is_replaying:
            if self.recorder_yaml is not None:
                self.tlsmate.recorder.serialize(self.get_yaml_file(self.recorder_yaml))

            if self.sp_out_yaml is not None:
                utils.serialize_data(
                    self.tlsmate.server_profile.make_serializable(),
                    file_name=self.get_yaml_file(self.sp_out_yaml),
                    replace=False,
                    indent=2,
                )

    def test_entry(self):
        """Entry point for pytest.
        """

        self.entry(is_replaying=True)
