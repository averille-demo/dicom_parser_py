"""DICOM centric utilities for tag data."""
__all__ = ["get_ast_functions", "init_logger", "limit_path", "parse_cmd_args",
           "show_data", "show_header"]
__author__ = "averille"
__email__ = "cloud.dev.apps@averille.com"
__license__ = "Apache 2.0"
__status__ = "demo"
__version__ = "1.6.5"

import os
import sys
import logging
import platform
import locale
import ast
from datetime import datetime
import pprint as pp
from typing import List, Dict
from pathlib import Path
import argparse
from pathvalidate.argparse import sanitize_filepath_arg

CWD_PATH = Path(__file__).resolve().parent
REPO_NAME = CWD_PATH.parent.name


def show_header() -> Dict:
    """
    Display dunder names: project status and environment information.

    Returns:
        None: results are printed to console
    """
    host_enc = locale.getpreferredencoding()
    host_arch = f"{platform.system()} {platform.architecture()[0]} {platform.machine()}"
    header = {
        "host": f"{platform.node():6} ({host_enc} {host_arch:16})",
        "python": platform.python_version(),
        "author": __author__,
        "status": __status__,
        "version": __version__,
        "license": __license__,
    }
    show_data(title=None, data=header)
    return header


def show_data(title: str = None, data: object = None, width=80) -> None:
    """
    Displays all data values in formatted output.

    Args:
        title (str): first line header string of data object
        data (object): List, Dict, Tuple formatted console output
        width (int): maximum width of per-line output

    Returns:
        None: results printed to console
    """
    if title:
        print(f"{title}")
    pp.pprint(object=data, indent=2, width=width, compact=True, sort_dicts=False)


def limit_path(
        path: Path,
        level=2,
        delimiter=os.path.sep,
) -> str:
    """
    Helper logging function: returns last n-level parts of path object

    Example: if level=2
        input: Path(drive:/parent/subdir1/subdir2/subdirN/data/filename.txt)
        output: 'data/filename.txt'

    Args:
        path (pathlib.Path): input path object
        level (int): number of path parts to include
        delimiter (str): character used to delimit path parts

    Returns:
        str: truncated path object as string
    """
    if level < 1:
        return f"{path}"
    return f"{delimiter.join(path.parts[-level:])}"


def get_ast_functions() -> None:
    """
    Open python module and list all functions/methods with abstract syntax tree (AST).

    Returns:
        None: results are printed to console
    """
    py_paths = [p.absolute() for p in sorted(CWD_PATH.glob(pattern="*.py")) if
                p.is_file()]
    for path in py_paths:
        functions = []
        with open(file=path, mode="r", encoding="utf-8") as fp:
            tree = ast.parse(source=fp.read(), filename=path.name)
            for func in tree.body:
                if isinstance(func, ast.FunctionDef):
                    functions.append(func.name)
            functions.sort()
        print(f"{limit_path(path, level=3)}\n__all__ = {functions}")


class SingleLineExceptionFormatter(logging.Formatter):
    """
    Helper class to ensure exceptions are formatted to single line in log file.
    https://docs.python.org/3/library/logging.html#logging.LogRecord

    Returns:
        logging.LogRecord: single line formatted string of exception
    """

    def format(self, record: logging.LogRecord) -> str:
        if record.exc_info:
            single_line = ""
            if record.msg:
                single_line += f"{record.msg} | "
            ex_type, ex_value, ex_tb = sys.exc_info()
            ex_type = f"{ex_type}" if ex_type else ""
            ex_value = " ".join(f"{str(ex_value)}".split()) if ex_value else ""
            src_name = f"{Path(ex_tb.tb_frame.f_code.co_filename).name}"
            line_num = f"{ex_tb.tb_lineno}"
            single_line += f"{ex_type} {ex_value} | {src_name}:{line_num}"
            record.msg = single_line
            record.exc_info = None
            record.exc_text = None
        return super().format(record)


def init_logger(
        log_name=REPO_NAME,
        log_file=Path(CWD_PATH, "logs", f"{REPO_NAME}.log"),
) -> logging.Logger:
    """
    Generate custom Logger object writes output to both file and standard output.
    Creates parent directories and blank log file (if missing)
    Args:
        log_name (str): name passed to getLogger()
        log_file (pathlib.Path): location where to save logging file output

    Returns:
        logging.Logger: instance based on name and file location
    """
    if not log_file.parent.exists():
        log_file.parent.mkdir(parents=True, exist_ok=True)
    if not log_file.is_file():
        log_file.touch(mode=0o777, exist_ok=True)

    # set name to caller module
    logger = logging.getLogger(name=log_name)
    logger.setLevel(logging.INFO)
    log_format = ("{asctime} [{levelname}]\t{name} | "
                  "{funcName}() line:{lineno} | {message}")
    datefmt = "%Y-%m-%d %H:%M:%S"
    log_fmt = SingleLineExceptionFormatter(
        fmt=log_format,
        datefmt=datefmt,
        style="{",
        validate=True,
    )
    # save to file
    file_hdlr = logging.FileHandler(log_file)
    file_hdlr.setLevel(logging.INFO)
    file_hdlr.setFormatter(fmt=log_fmt)
    logger.addHandler(file_hdlr)

    # display log in console
    stdout_hdlr = logging.StreamHandler(sys.stdout)
    stdout_hdlr.setLevel(logging.DEBUG)
    stdout_hdlr.setFormatter(fmt=log_fmt)
    logger.addHandler(stdout_hdlr)
    return logger


def get_timestamp() -> str:
    """get timestamp from current time"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S %p')


def parse_cmd_args() -> Dict:
    """
    Command line argument options to enable alternative input/output/dump paths.

    Returns:
        Dict: key:value pairs of validated command line arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input_path",
        type=sanitize_filepath_arg,
        default=Path(CWD_PATH.parent, "data", "input"),
        required=False,
        help="path to source directory containing DICOM files (.dcm, .dicom)",
    )
    parser.add_argument(
        "-o",
        "--output_path",
        type=sanitize_filepath_arg,
        default=Path(CWD_PATH.parent, "data", "output"),
        required=False,
        help="path to output directory for extracts (.csv, .json)",
    )
    parser.add_argument(
        "-d",
        "--dump_path",
        type=sanitize_filepath_arg,
        default=Path(CWD_PATH.parent, "data", "tag_dumps"),
        required=False,
        help="path to output directory for DICOM tag dumps (all tags)",
    )
    args = vars(parser.parse_args())
    for cmd_arg in ["input_path", "output_path", "dump_path"]:
        path_str = str(args[cmd_arg])
        # convert str to pathlib object
        args[cmd_arg] = Path(args[cmd_arg])
        # validate if path is exists and is directory
        if not args[cmd_arg].is_dir():
            parser.error(f"invalid path: '{path_str}'")
            args[cmd_arg] = None
    return args
