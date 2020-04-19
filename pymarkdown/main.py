"""
Module to provide for a simple implementation of a title case algorithm.
"""
import argparse
import json
import logging
import os
import sys
import traceback

from pymarkdown.bad_tokenization_error import BadTokenizationError
from pymarkdown.plugin_manager import BadPluginError, PluginManager
from pymarkdown.source_providers import FileSourceProvider
from pymarkdown.tokenized_markdown import TokenizedMarkdown


# https://github.com/hiddenillusion/example-code/commit/3e2daada652fe9b487574c784e0924bd5fcfe667
# TODO check
class PyMarkdownLint:
    """
    Class to provide for a simple implementation of a title case algorithm.
    """

    def __init__(self):
        self.__version_number = "0.1.0"
        self.__show_stack_trace = False

        self.__plugins = PluginManager()
        self.__tokenizer = None
        self.logger = logging.getLogger(__name__)

    def __parse_arguments(self):
        parser = argparse.ArgumentParser(description="Lint any found Markdown files.")

        parser.add_argument(
            "--version", action="version", version="%(prog)s " + self.__version_number
        )

        parser.add_argument(
            "-l",
            "--list-files",
            dest="list_files",
            action="store_true",
            default=False,
            help="list the markdown files found and exit",
        )
        parser.add_argument(
            "-e",
            "--enable-rules",
            dest="enable_rules",
            action="store",
            default="",
            help="comma separated list of rules to enable",
        )
        parser.add_argument(
            "-d",
            "--disable-rules",
            dest="disable_rules",
            action="store",
            default="",
            help="comma separated list of rules to disable",
        )
        parser.add_argument(
            "-x-scan",
            dest="x_test_scan_fault",
            action="store_true",
            default="",
            help=argparse.SUPPRESS,
        )
        parser.add_argument(
            "-x-init",
            dest="x_test_init_fault",
            action="store_true",
            default="",
            help=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--add-plugin",
            dest="add_plugin",
            action="append",
            default=None,
            help="path to a plugin containing a new rule to apply",
        )
        parser.add_argument(
            "--config",
            "-c",
            dest="configuration_file",
            action="store",
            default=None,
            help="path to a configuration file",
        )
        parser.add_argument(
            "--stack-trace",
            dest="show_stack_trace",
            action="store_true",
            default=False,
            help="if an error occurs, print out the stack trace for debug purposes",
        )
        parser.add_argument(
            "paths",
            metavar="path",
            type=str,
            nargs="+",
            help="One or more paths to scan for eligible files",
        )
        return parser.parse_args()

    @classmethod
    def is_file_eligible_to_scan(cls, path_to_test):
        """
        Determine if the presented path is one that we want to scan.
        """
        return path_to_test.endswith(".md")

    # pylint: disable=broad-except
    def __scan_file(self, args, next_file):
        """
        Scan a given file and call the plugin manager for any significant events.
        """

        source_provider = FileSourceProvider(next_file)

        line_number = 1
        next_line = source_provider.get_next_line()
        context = self.__plugins.starting_new_file(next_file)
        while next_line is not None:
            self.__plugins.next_line(context, line_number, next_line)
            line_number += 1
            next_line = source_provider.get_next_line()

        source_provider = FileSourceProvider(next_file)
        if args.x_test_scan_fault:
            source_provider = None
        actual_tokens = self.__tokenizer.transform_from_provider(source_provider)

        for next_token in actual_tokens:
            self.__plugins.next_token(context, next_token)

        self.__plugins.completed_file(context, line_number)

    # pylint: enable=broad-except

    @classmethod
    def __determine_files_to_scan(cls, eligible_paths):

        files_to_parse = set()
        for next_path in eligible_paths:

            if not os.path.exists(next_path):
                print(
                    "Provided path '" + next_path + "' does not exist. Skipping.",
                    file=sys.stderr,
                )
                continue
            if os.path.isdir(next_path):
                for root, _, files in os.walk(next_path):
                    for file in files:
                        rooted_file_path = root + "/" + file
                        if cls.is_file_eligible_to_scan(rooted_file_path):
                            files_to_parse.add(rooted_file_path)
            else:
                if cls.is_file_eligible_to_scan(next_path):
                    files_to_parse.add(next_path)
                else:
                    print(
                        "Provided file path '"
                        + next_path
                        + "' is not a valid markdown file. Skipping.",
                        file=sys.stderr,
                    )
        files_to_parse = list(files_to_parse)
        files_to_parse.sort()
        return files_to_parse

    @classmethod
    def __handle_list_files(cls, files_to_scan):

        if files_to_scan:
            print("\n".join(files_to_scan))
            return 0
        print("No Markdown files found.", file=sys.stderr)
        return 1

    def load_json_configuration(self, configuration_file):
        """
        Load the configuration from a json file.
        """

        configuration_map = {}
        try:
            with open(configuration_file) as infile:
                configuration_map = json.load(infile)
        except json.decoder.JSONDecodeError as ex:
            formatted_error = (
                "Specified configuration file '"
                + configuration_file
                + "' is not a valid JSON file ("
                + str(ex)
                + ")."
            )
            self.__handle_error(formatted_error)
        except IOError as ex:
            formatted_error = (
                "Specified configuration file '"
                + configuration_file
                + "' was not loaded ("
                + str(ex)
                + ")."
            )
            self.__handle_error(formatted_error)

        return configuration_map

    def __load_configuration_and_apply_to_plugins(self, args):

        loaded_configuration_map = {}
        if args.configuration_file:
            loaded_configuration_map = self.load_json_configuration(
                args.configuration_file
            )

        try:
            self.__plugins.apply_configuration(loaded_configuration_map)
        except BadPluginError as this_exception:
            formatted_error = (
                str(type(this_exception).__name__)
                + " encountered while configuring plugins:\n"
                + str(this_exception)
            )
            self.__handle_error(formatted_error)

    def __initialize_parser(self, args):

        resource_path = None
        if args.x_test_init_fault:
            resource_path = "fredo"

        try:
            self.__tokenizer = TokenizedMarkdown(resource_path)
        except BadTokenizationError as this_exception:
            formatted_error = (
                str(type(this_exception).__name__)
                + " encountered while initializing tokenizer:\n"
                + str(this_exception)
            )
            self.__handle_error(formatted_error)

    def __initialize_plugins(self, args, plugin_dir):
        """
        Make sure all plugins are ready before being initialized.
        """

        self.__plugins = PluginManager()
        try:
            self.__plugins.initialize(
                plugin_dir, args.add_plugin, args.enable_rules, args.disable_rules
            )
        except BadPluginError as this_exception:
            formatted_error = (
                "BadPluginError encountered while loading plugins:\n"
                + str(this_exception)
            )
            self.__handle_error(formatted_error)

    def __handle_error(self, formatted_error):

        self.logger.warning(formatted_error, exc_info=True)
        print(formatted_error, file=sys.stderr)
        if self.__show_stack_trace:
            traceback.print_exc(file=sys.stderr)
        sys.exit(1)

    def __handle_scan_error(self, next_file, this_exception):

        formatted_error = (
            str(type(this_exception).__name__)
            + " encountered while scanning '"
            + next_file
            + "':\n"
            + str(this_exception)
        )
        self.__handle_error(formatted_error)

    def main(self):
        """
        Main entrance point.
        """
        args = self.__parse_arguments()
        self.__show_stack_trace = args.show_stack_trace

        # logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        base_logger = logging.getLogger()
        base_logger.setLevel(logging.DEBUG)

        files_to_scan = self.__determine_files_to_scan(args.paths)
        if args.list_files:
            return_code = self.__handle_list_files(files_to_scan)
            sys.exit(return_code)

        plugin_dir = os.path.dirname(os.path.realpath(__file__))
        plugin_dir = os.path.join(plugin_dir, "plugins")
        self.__initialize_plugins(args, plugin_dir)

        self.__initialize_parser(args)

        self.__load_configuration_and_apply_to_plugins(args)

        for next_file in files_to_scan:
            try:
                self.__scan_file(args, next_file)
            except BadPluginError as this_exception:
                self.__handle_scan_error(next_file, this_exception)
            except BadTokenizationError as this_exception:
                self.__handle_scan_error(next_file, this_exception)

        if self.__plugins.number_of_scan_failures:
            sys.exit(1)


if __name__ == "__main__":
    PyMarkdownLint().main()
