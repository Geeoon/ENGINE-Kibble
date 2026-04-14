"""
Author: hshultz
Created: 02/09/2026
Copyright (c) 2026 Innoflight, LLC. All Rights Reserved
"""
__all__ = [
    "MultilineFormatter",
    "MultilineColoredFormatter",
    "setup_minimal_logger",
    "setup_default_logger",
]

import textwrap
import logging
import sys
from typing import Any, TextIO

try:
    from coloredlogs import ColoredFormatter

    coloredlogs_found = True
except ModuleNotFoundError:
    coloredlogs_found = False


class MultilineFormatter(logging.Formatter):  # pragma: no coverage
    """Formatter to indent multiline messages so they are aligned."""

    def __init__(self, fmt=None, multiline_offset=4):
        logging.Formatter.__init__(self, fmt=fmt)
        # This is just set so the __init__ matches MultilineColoredFormatter
        self.mo = multiline_offset

    def format(self, record):
        # Save original record properties
        msg = record.msg
        exc_txt = record.exc_text
        exc_info = record.exc_info
        args = record.args

        # Remove message, args, and traceback info
        record.msg = ""
        record.exc_text = None
        record.exc_info = None
        record.args = tuple()

        # Set attribute for creation time in seconds since program start
        record.relativeCreatedSecs = record.relativeCreated / 1000.0

        # Format record with properties removed to get just the formatted
        # prefix
        prefix = logging.Formatter.format(self, record)

        # Restore original record properties
        record.msg = msg
        record.exc_text = exc_txt
        record.exc_info = exc_info
        record.args = args

        # Format the full message
        msg = logging.Formatter("%(message)s").format(record)

        # Pad continuation lines in the message to match prefix length
        new_msg = textwrap.indent(msg, " " * len(prefix)).lstrip()

        # Return full message with prefix and padded message
        return prefix + new_msg


# If the coloredlogs package isn't found, alias MultilineColoredFormatter
# to the normal, non-colored MultilineFormatter
if not coloredlogs_found:
    MultilineColoredFormatter = MultilineFormatter
else:
    class MultilineColoredFormatter(ColoredFormatter):  # pragma: no coverage
        """
        MultilineFormatter that colorizes output using ASNI escape
        sequences
        """

        def __init__(
                self,
                fmt=None,
                level_styles=None,
                field_styles=None,
                multiline_offset=4
        ):

            self.mo = multiline_offset

            if not level_styles:
                level_styles = {
                    "verbose": {"color": "blue"},
                    "debug": {"color": "green"},
                    "info": {},
                    "warning": {"color": "yellow"},
                    "error": {"color": "red"},
                    "critical": {"color": "red", "bold": True},
                    "comment": {"color": "white", "bold": True},
                }

            if not field_styles:
                field_styles = {
                    "asctime": {"color": "green"},
                    "hostname": {"color": "magenta"},
                    "levelname": {"color": "white", "bold": True},
                    "name": {"color": "cyan"},
                    "programname": {"color": "cyan"},
                    "username": {"color": "yellow"},
                }

            ColoredFormatter.__init__(
                self,
                fmt=fmt,
                level_styles=level_styles,
                field_styles=field_styles
            )

            self.original_fmt = fmt

        def format(self, record):
            # Save original record properties
            msg = record.msg
            exc_txt = record.exc_text
            exc_info = record.exc_info
            args = record.args

            # Remove message, args, and traceback info
            record.msg = ""
            record.exc_text = None
            record.exc_info = None
            record.args = tuple()

            # Set attribute for creation time in seconds since program start
            record.relativeCreatedSecs = record.relativeCreated / 1000.0

            # Format record with properties removed to get just the formatted
            # prefix
            prefix = logging.Formatter(self.original_fmt).format(record)
            colored_prefix = ColoredFormatter.format(self, record)

            # Restore original record properties
            record.msg = msg
            record.exc_text = exc_txt
            record.exc_info = exc_info
            record.args = args

            # Format the full message
            msg = ColoredFormatter(
                "%(message)s",
                level_styles=self.level_styles,
                field_styles=self.field_styles
            ).format(record)

            # No clue why this needs a -4. Because of the ANSI characters?
            # Pad continuation lines in the message to match prefix length
            new_msg = textwrap.indent(
                msg, " " * (len(prefix) - self.mo)
            ).lstrip()

            # Return full message with prefix and padded message
            return colored_prefix + new_msg


def _configure_package_log_levels() -> None:
    """
    Configures log levels for some chatty packages.
    """
    # Pymongo logging at info level can cause a feedback loop with the
    # db driver
    # TODO: In the future we may want to just limit this for the DB handler
    #       and not the console handler
    pymongo_logger = logging.getLogger("pymongo")
    pymongo_logger.setLevel(logging.INFO)

    # Numba logs a lot
    numba_logger = logging.getLogger("numba")
    numba_logger.setLevel(logging.WARNING)

    # Pyvisa also logs a lot
    pyvisa_logger = logging.getLogger("pyvisa")
    pyvisa_logger.setLevel(logging.INFO)

    # So does paramiko/urllib3
    paramiko_logger = logging.getLogger("paramiko")
    paramiko_logger.setLevel(logging.INFO)
    urllib_logger = logging.getLogger("urllib3")
    urllib_logger.setLevel(logging.INFO)

    # And can
    can_logger = logging.getLogger("can")
    can_logger.setLevel(logging.INFO)


def _create_console_handler(
        fmt: str,
        display_level: int,
        colored: bool,
        mo: int = 0,
        stream: TextIO | Any = sys.stdout
) -> logging.StreamHandler:
    """
    Creates and configures a logging StreamHandler.

    :param fmt: Log format string to configure Formatter with
    :param display_level: Minimum log level to display
    :param colored: If coloredlogs should be enabled (if installed)
    :param mo: Multiline-offset. Used to adjust multiline alignment when
        coloredlogs are used
    :param stream: Output stream for StreamHandler
    :return: new StreamHandler
    """
    ch = logging.StreamHandler(stream)
    if colored:
        cf = MultilineColoredFormatter(fmt, multiline_offset=mo)
    else:
        cf = MultilineFormatter(fmt)
    ch.setFormatter(cf)
    ch.setLevel(display_level)
    return ch


def setup_minimal_logger(
        display_level: int = logging.DEBUG,
        log_level: int = logging.NOTSET,
        show_level: bool = False,
        colored: bool = False,
) -> logging.Logger:  # pragma: no coverage
    """
    Configures and returns the CATS "minimal" root logger.

    This will configure and connect a STDOUT StreamHandler with a
    (optionally colored) multiline log formatter. Logs will only include
    the time in seconds since program start and the log message. If
    ``show_level`` is enabled, the log level name will also be included.

    :param display_level: Minimum log level to display. All logs at this
        level or higher will be printed.
    :param log_level: Minimum log level to capture. All logs at this
        level or higher will be captured by the root logger.
    :param colored: If coloredlogs should be enabled (if installed).
    :param show_level: If the log level name should be included in log
        lines
    :return: Root logger
    """
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Console handler (console log output)
    fmt = "%(relativeCreatedSecs)9.3f | %(message)s"

    if show_level:
        fmt = "%(relativeCreatedSecs)9.3f | %(levelname)-7s | %(message)s"

    logger.addHandler(
        _create_console_handler(fmt, display_level, colored)
    )
    _configure_package_log_levels()

    return logger


def setup_default_logger(
        display_level: int = logging.DEBUG,
        log_level: int = logging.NOTSET,
        colored: bool = True,
        name_width: int = 50,
) -> logging.Logger:  # pragma: no coverage
    """
    Configures and returns the CATS "default" root logger.

    This will configure and connect a STDOUT StreamHandler with a
    (optionally colored) multiline log formatter. If ``display_level`` is
    set at 20 or higher, only the log level name and message will be
    printed. At levels lower than 20, the time and logger name will also
    be printed.

    :param display_level: Minimum log level to display. All logs at this
        level or higher will be printed
    :param log_level: Minimum log level to capture. All logs at this
        level or higher will be captured by the root logger
    :param colored: If coloredlogs should be enabled (if installed)
    :param name_width: Number of characters to reserve for loger name
        (if ``display_level`` <20)
    :return: Root logger
    """
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Console handler (console log output)
    long_fmt = (
        f"%(asctime)-19s - %(levelname)-7s - "
        f"%(name)-{name_width}s - %(message)s"
    )
    fmt = long_fmt
    mo = 4

    if display_level >= 20:
        fmt = "%(levelname)-11s - %(message)s"
        mo = 0

    logger.addHandler(
        _create_console_handler(fmt, display_level, colored, mo)
    )
    _configure_package_log_levels()

    return logger
