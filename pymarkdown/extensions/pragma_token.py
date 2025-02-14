"""
Module to provide for linter instructions that can be embedded within the document.
"""
import logging
from typing import Callable, Dict, Optional, Set

from application_properties import ApplicationPropertiesFacade

from pymarkdown.container_blocks.parse_block_pass_properties import (
    ParseBlockPassProperties,
)
from pymarkdown.extension_manager.extension_impl import ExtensionDetails
from pymarkdown.extension_manager.extension_manager_constants import (
    ExtensionManagerConstants,
)
from pymarkdown.extension_manager.parser_extension import ParserExtension
from pymarkdown.markdown_token import MarkdownToken, MarkdownTokenClass
from pymarkdown.parser_helper import ParserHelper
from pymarkdown.parser_logger import ParserLogger
from pymarkdown.plugin_manager.found_plugin import FoundPlugin
from pymarkdown.position_marker import PositionMarker

POGGER = ParserLogger(logging.getLogger(__name__))


class PragmaExtension(ParserExtension):
    """
    Extension to implement the pragma extensions.
    """

    def get_identifier(self) -> str:
        """
        Get the identifier associated with this extension.
        """
        return "linter-pragmas"

    def get_details(self) -> ExtensionDetails:
        """
        Get the details for the extension.
        """
        return ExtensionDetails(
            extension_id=self.get_identifier(),
            extension_name="Pragma Linter Instructions",
            extension_description="Allows parsing of instructions for the linter.",
            extension_enabled_by_default=True,
            extension_version="0.5.0",
            extension_interface_version=ExtensionManagerConstants.EXTENSION_INTERFACE_VERSION_BASIC,
            extension_url="https://github.com/jackdewinter/pymarkdown/blob/main/docs/extensions/pragmas.md",
            extension_configuration=None,
        )

    def apply_configuration(
        self, extension_specific_facade: ApplicationPropertiesFacade
    ) -> None:
        """
        Apply any configuration required by the extension.
        """
        _ = extension_specific_facade

    @staticmethod
    def look_for_pragmas(
        position_marker: PositionMarker,
        line_to_parse: str,
        container_depth: int,
        extracted_whitespace: Optional[str],
        parser_properties: ParseBlockPassProperties,
    ) -> bool:
        """
        Look for a pragma in the current line.
        """

        POGGER.debug("look_for_pragmas - >$<", line_to_parse)
        POGGER.debug("look_for_pragmas - ws >$<", extracted_whitespace)
        if (
            not container_depth
            and not extracted_whitespace
            and (
                line_to_parse.startswith(PragmaToken.pragma_prefix)
                or line_to_parse.startswith(PragmaToken.pragma_alternate_prefix)
            )
        ):
            was_extended_prefix = line_to_parse.startswith(
                PragmaToken.pragma_alternate_prefix
            )

            start_index, _ = ParserHelper.extract_spaces(
                line_to_parse,
                len(
                    PragmaToken.pragma_alternate_prefix
                    if was_extended_prefix
                    else PragmaToken.pragma_prefix
                ),
            )
            remaining_line = line_to_parse[start_index:].rstrip().lower()
            if remaining_line.startswith(
                PragmaToken.pragma_title
            ) and remaining_line.endswith(PragmaToken.pragma_suffix):
                index_number = (
                    -position_marker.line_number
                    if was_extended_prefix
                    else position_marker.line_number
                )
                parser_properties.pragma_lines[index_number] = line_to_parse
                POGGER.debug("pragma $ extracted - >$<", index_number, line_to_parse)
                return True
        POGGER.debug("pragma not extracted - >$<", line_to_parse)
        return False

    # pylint: disable=too-many-arguments
    @staticmethod
    def compile_single_pragma(
        scan_file: str,
        next_line_number: int,
        pragma_lines: Dict[int, str],
        all_ids: Dict[str, FoundPlugin],
        document_pragmas: Dict[int, Set[str]],
        log_pragma_failure: Callable[[str, int, str], None],
    ) -> None:
        """
        Compile a single pragma line, validating it before adding it to the dictionary of pragmas.
        """
        if next_line_number > 0:
            prefix_length = len(PragmaToken.pragma_prefix)
            actual_line_number = next_line_number
        else:
            prefix_length = len(PragmaToken.pragma_alternate_prefix)
            actual_line_number = -next_line_number

        line_after_prefix = pragma_lines[next_line_number][prefix_length:].rstrip()
        after_whitespace_index, _ = ParserHelper.extract_spaces(line_after_prefix, 0)
        assert after_whitespace_index is not None
        command_data = line_after_prefix[
            after_whitespace_index
            + len(PragmaToken.pragma_title) : -len(PragmaToken.pragma_suffix)
        ]
        after_command_index, command = ParserHelper.extract_until_spaces(
            command_data, 0
        )
        assert command is not None
        assert after_command_index is not None
        command = command.lower()
        if not command:
            log_pragma_failure(
                scan_file,
                actual_line_number,
                "Inline configuration specified without command.",
            )
        elif command == "disable-next-line":
            PragmaExtension.__handle_disable_next_line(
                command_data,
                after_command_index,
                log_pragma_failure,
                scan_file,
                actual_line_number,
                document_pragmas,
                all_ids,
                command,
            )
        else:
            log_pragma_failure(
                scan_file,
                actual_line_number,
                f"Inline configuration command '{command}' not understood.",
            )

    # pylint: enable=too-many-arguments

    # pylint: disable=too-many-arguments
    @staticmethod
    def __handle_disable_next_line(
        command_data: str,
        after_command_index: int,
        log_pragma_failure: Callable[[str, int, str], None],
        scan_file: str,
        actual_line_number: int,
        document_pragmas: Dict[int, Set[str]],
        all_ids: Dict[str, FoundPlugin],
        command: str,
    ) -> None:
        ids_to_disable = command_data[after_command_index:].split(",")
        processed_ids = set()
        for next_id in ids_to_disable:
            next_id = next_id.strip().lower()
            if not next_id:
                log_pragma_failure(
                    scan_file,
                    actual_line_number,
                    f"Inline configuration command '{command}' specified a plugin with a blank id.",
                )
            elif next_id in all_ids:
                normalized_id = all_ids[next_id].plugin_id
                processed_ids.add(normalized_id)
            else:
                log_pragma_failure(
                    scan_file,
                    actual_line_number,
                    f"Inline configuration command '{command}' unable to find a plugin with the id '{next_id}'.",
                )

        if processed_ids:
            document_pragmas[actual_line_number + 1] = processed_ids

    # pylint: enable=too-many-arguments


class PragmaToken(MarkdownToken):
    """
    Token that contains the pragmas for the document.
    """

    pragma_prefix = "<!--"
    pragma_alternate_prefix = "<!---"
    pragma_title = "pyml "
    pragma_suffix = "-->"

    def __init__(self, pragma_lines: Dict[int, str]) -> None:
        self.__pragma_lines = pragma_lines

        serialized_pragmas = "".join(
            f";{next_line_number}:{pragma_lines[next_line_number]}"
            for next_line_number in pragma_lines
        )

        MarkdownToken.__init__(
            self,
            MarkdownToken._token_pragma,
            MarkdownTokenClass.SPECIAL,
            is_extension=True,
            extra_data=serialized_pragmas[1:],
        )

    @property
    def pragma_lines(self) -> Dict[int, str]:
        """
        Returns the pragma lines for the document.
        """
        return self.__pragma_lines
