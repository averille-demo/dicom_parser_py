"""
Module to extract selected DICOM attributes/tags values from '.dcm' files using pydicom.

http://dicomlookup.com/lookup.asp
example DICOM Attribute: modality           1:M (one Attribute may have many Tags)
example DICOM Tag:      (0x0008, 0x0060)    1:1 mapping
"""
import string
import time
from datetime import datetime
from typing import List, Dict
from pathlib import Path
import pandas as pd
import pydicom
from pydicom.tag import Tag
from pydicom.errors import InvalidDicomError

from dcm_lib import init_logger, limit_path, parse_cmd_args, show_header

MODULE = Path(__file__).resolve().stem
CWD_PATH = Path(__file__).resolve().parent


def find_dicom(
        src_folder: Path,
        file_ext: str = ".dcm",
        include_recursive: bool = False,
) -> List:
    """
    Get paths to valid DICOM files (optional: include sub-folders).

    Args:
        src_folder (pathlib.Path): path to directory containing DICOM files
        file_ext (str): '.dcm' or '.dicom'
        include_recursive (bool): optional to include subfolders in search

    Returns:
        List[pathlib.Path]: objects pointing to DICOM files
    """
    file_paths = []
    if src_folder.is_dir() and file_ext.lower() in [".dcm", ".dicom", ".gz", ".nii"]:
        if include_recursive:
            glob = locals()["src_folder"].rglob
        else:
            glob = locals()["src_folder"].glob
        file_paths = [
            p.absolute() for p in sorted(glob(pattern=f"*{file_ext}")) if p.is_file()
        ]
    logger.info(
        f"found ({len(file_paths)}) '{file_ext}' files recursive={include_recursive})"
    )
    return file_paths


def sanitize_tag(raw: str = "") -> str:
    """
    Remove invalid characters from DICOM tag value
    string.punctuation: !"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~
    Args:
        raw (str): value from DICOM tag

    Returns:
        str: sanitized string
    """
    # remove newlines and tab control characters
    invalid = list(string.punctuation + "\t" + "\n")
    # retain valid chars (if present in tag values)
    for keep in ["-", "+", "_", ":", ".", "|"]:
        invalid.remove(keep)
    clean = ""
    # remove specific symbols
    for char in raw:
        if char not in invalid:
            clean += char
    # replace all double spaces with single (if present)
    while "  " in clean:
        clean = clean.replace("  ", " ")
    return clean


def dump_tags_to_txt(
        src_dcm: Path,
        dst_folder: Path,
) -> bool:
    """
    Dump all tags (pydicom dataset) from single DICOM file to text file.
    Args:
        src_dcm (pathlib.Path): path to single DICOM file
        dst_folder (pathlib.Path): path to output directory to store text dump

    Returns:
        bool: validation check to ensure text dump file was successfully created
    """
    try:
        if not dst_folder.exists():
            dst_folder.mkdir(exist_ok=True, parents=True)
        dump_path = dst_folder.joinpath(*[f"{src_dcm.stem}.txt"])
        # create tag dump file, read only metadata (no pixels)
        with pydicom.dcmread(src_dcm, stop_before_pixels=True) as ds:
            with open(dump_path, "w", encoding="utf-8") as fp:
                fp.write(str(ds))
            if dump_path.is_file() and dump_path.stat().st_size > 0:
                return True
    except (OSError, PermissionError, ValueError, InvalidDicomError):
        logger.exception(msg=f"{limit_path(src_dcm)}")
    return False


def dump_dicom_all_tags(
        dicom_paths: List,
        dst_folder: Path,
) -> None:
    """
    Dump all tags from DICOM files to per-image text file.

    Step 1: Creates parent folder if needed
    Step 2: Removes all prior dump text files in parent folder
    Step 3: For each .dcm in dicom_paths, extract all DICOM tags to .txt file

    Args:
        dicom_paths (List): all paths to DICOM files
        dst_folder (pathlib.Path): output directory to store DICOM dump .txt files

    Returns:
        None
    """
    if not dst_folder.exists():
        dst_folder.mkdir(exist_ok=True, parents=True)

    # remove all prior dumps in ./data/tag_dumps/
    txt_paths = [
        p.absolute()
        for p in sorted(dst_folder.glob(pattern="*.txt"))
        if p.is_file()
    ]
    logger.info(f"purged ({len(txt_paths)}) prior '.txt' files: {limit_path(dst_folder)}")
    for txt_path in txt_paths:
        txt_path.unlink(missing_ok=True)

    # create new tag dumps
    for dcm_path in dicom_paths:
        dump_tags_to_txt(src_dcm=dcm_path, dst_folder=dst_folder)
    logger.info(f"dumped ({len(dicom_paths)}) DICOM files: {limit_path(dst_folder)}")


def get_transfer_syntax_map(include_reverse: bool = False) -> Dict:
    """
    mapping: common transfer syntax UID to names found in pydicom
    source: https://github.com/pydicom/pydicom/blob/master/pydicom/uid.py
    Args:
        include_reverse (bool): optional to include reverse mapping of {value: key} pairs

    Returns:
        Dict: {key: value} pairs of common DICOM transfer syntax
    """
    transfer_syntax_map = dict(
        [
            ("1.2.840.10008.1.2", "ImplicitVRLittleEndian"),
            ("1.2.840.10008.1.2.1", "ExplicitVRLittleEndian"),
            ("1.2.840.10008.1.2.2", "ExplicitVRBigEndian"),
            ("1.2.840.10008.1.2.4.50", "JPEGBaseLineLossy8bit"),
            ("1.2.840.10008.1.2.4.51", "JPEGBaseLineLossy12bit"),
            ("1.2.840.10008.1.2.4.70", "JPEGLossless"),
            ("1.2.840.10008.1.2.4.80", "JPEGLSLossless"),
            ("1.2.840.10008.1.2.4.90", "JPEG2000Lossless"),
            ("1.2.840.10008.1.2.4.91", "JPEG2000Lossy"),
            ("1.2.840.10008.1.2.5", "RLELossless"),
        ]
    )
    if include_reverse:
        transfer_syntax_map.update({v: k for k, v in transfer_syntax_map.items()})
    return transfer_syntax_map


def map_tag_objects() -> Dict:
    """
    Creates mapping of pydicom.tag.BaseTag(00##,00##)
    represented as ds[0x0008,0x0050].value in pydicom objects
    keys are used as header row for output files

    Returns:
         Dict: ordered {key: value} pairs of desired attributes to extract from DICOMs
    """
    return dict(
        [
            ("modality", Tag(0x0008, 0x0060)),
            ("sopInstanceUid", Tag(0x0002, 0x0003)),
            ("institution_name", Tag(0x0008, 0x0080)),
            ("manufacturer", Tag(0x0008, 0x0070)),
            ("manufacturer_model", Tag(0x0008, 0x1090)),
            ("sourceAET", Tag(0x0002, 0x0016)),
            ("station_name", Tag(0x0008, 0x1010)),
            ("study_description", Tag(0x0008, 0x1030)),
            ("study_date", Tag(0x0008, 0x0020)),
            ("study_time", Tag(0x0008, 0x0030)),
            ("transferSyntaxUid", Tag(0x0002, 0x0010)),
        ]
    )


def init_header_map(filename: str) -> Dict:
    """
    Returns attribute key/value pairs in specific order (default: empty string).
    Args:
        filename (str): path.name of specific DICOM to extract tag values

    Returns:
        Dict: ordered {key: value} pairs of desired DICOM attributes to extract
    """
    default_str = ""
    headers = ["filename"]
    headers.extend(list(map_tag_objects().keys()))
    hdr_map = {hdr: default_str for hdr in headers}
    hdr_map["filename"] = filename
    return hdr_map


def parse_tags(
        dicom_paths: List,
        sanitize_values: bool = False,
) -> List:
    """
    step 1: find valid '.dcm/.dicom' files from source directory
    step 2: extract selected DICOM tags using pydicom
    metadata: SOP UID, source AET and transfer syntax UID
    dataset: other tags of interest

    Args:
        dicom_paths (List): paths to DICOM files
        sanitize_values (bool): optional to sanitize DICOM tag value

    Returns:
        List: extracted DICOM tag values for all '.dcm/.dicom' files in dicom_paths
    """
    tag_dumps = []
    syntax_map = get_transfer_syntax_map()
    for src_dcm in dicom_paths:
        extract = init_header_map(filename=src_dcm.name)
        try:
            if not pydicom.misc.is_dicom(src_dcm):
                raise InvalidDicomError
            with pydicom.dcmread(src_dcm, stop_before_pixels=True) as ds:
                for attr, tag_obj in map_tag_objects().items():
                    # extract metadata values
                    if attr in ["sopInstanceUid", "sourceAET", "transferSyntaxUid"]:
                        if tag_obj in ds.file_meta:
                            extract[attr] = ds.file_meta[tag_obj].value
                            extract["transferSyntaxName"] = syntax_map.get(
                                ds.file_meta[tag_obj].value, ""
                            )
                    # extract specific tags
                    elif tag_obj in ds.keys():
                        tag_val = ds[tag_obj].value
                        if sanitize_values:
                            tag_val = sanitize_tag(tag_val)
                        extract[attr] = tag_val
                logger.info(msg=f"{limit_path(path=src_dcm)}")
                tag_dumps.append(extract)
        except (OSError, ValueError, KeyError, InvalidDicomError):
            logger.exception(msg=f"{limit_path(src_dcm)}")
    return tag_dumps


def extract_to_df(
        dicom_paths: List,
) -> pd.DataFrame:
    """
    step 3: store data in pandas dataframe (df)
    step 4: convert df columns (as needed)

    Args:
        dicom_paths (List): paths to DICOM files

    Returns:
        pd.DataFrame: extracted tag values (all DICOMs) stored in pandas
    """
    try:
        # extract specific tag data
        tag_dumps = parse_tags(dicom_paths=dicom_paths)
        if len(tag_dumps) > 0:
            df = pd.DataFrame(tag_dumps)
            df["extract_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if "study_date" in df.columns.tolist():
                # convert strings to pandas date dtypes
                df["study_date"] = pd.to_datetime(df["study_date"], errors="coerce")
                # ensure YYYY-MM-DD format
                df["study_date"] = df["study_date"].dt.strftime("%Y-%m-%d")

            if "study_time" in df.columns.tolist():
                # convert float/int strings (in seconds since Epoch) to pandas timestamp
                df["study_time"] = pd.to_datetime(
                    df["study_time"],
                    unit="s",
                    errors="coerce",
                )
                # ensure 'HH:MM:SS AM/PM' format
                df["study_time"] = df["study_time"].dt.strftime("%H:%M:%S %p")
            return df
    except (PermissionError, ValueError, pd.errors.DtypeWarning):
        logger.exception(msg="extract error")
    return None


def write_to_file(
        df: pd.DataFrame,
        dst_folder=Path(CWD_PATH.parent, "data", "output"),
) -> bool:
    """
    step 5: delete all extracts from previous run
    step 6: save updated extracts to '.csv/.json'

    Args:
        df (pd.DataFrame): pandas dataframe with ordered columns of tag extracts
        dst_folder (pathlib.Path): output directory to save .csv/.json extracts

    Returns:
        bool: validation check to ensure .csv/.json files were successfully created
    """
    is_csv_saved = False
    is_json_saved = False
    try:
        json_path = dst_folder.joinpath(*[f"{MODULE}.json"])
        if json_path.is_file():
            json_path.unlink(missing_ok=True)

        # create newline delimited JSON in {key: value} format
        df.to_json(json_path, orient="records", lines=True)
        if json_path.is_file() and json_path.stat().st_size > 0:
            is_json_saved = True
            logger.info(msg=f"{limit_path(path=json_path)}")

        csv_path = dst_folder.joinpath(*[f"{MODULE}.csv"])
        if csv_path.is_file():
            csv_path.unlink(missing_ok=True)
        # create new fully quoted csv extract (comma delimited)
        df.to_csv(
            csv_path,
            sep=",",
            date_format="%Y-%m-%d",
            encoding="utf-8",
            quoting=1,
            quotechar='"',
            index=False,
            header=True,
        )
        if csv_path.is_file() and csv_path.stat().st_size > 0:
            is_csv_saved = True
            logger.info(msg=f"{limit_path(path=csv_path)}")
    except (PermissionError, ValueError, pd.errors.DtypeWarning):
        logger.exception(msg=f"{limit_path(path=csv_path)}")
    return is_csv_saved and is_json_saved


def run_pipeline() -> None:
    """
    step 1: find valid '.dcm' files from source directory
    step 2: extract selected DICOM tags using pydicom
    step 3: store data in pandas dataframe (df)
    step 4: convert df columns (as needed)
    step 5: delete extracts from previous run
    step 6: save extracts to '.csv/.json'
    """
    timer = time.perf_counter()
    show_header()

    dicom_paths = find_dicom(src_folder=cmd_args["input_path"], include_recursive=False)
    df = extract_to_df(dicom_paths=dicom_paths)
    write_to_file(df=df, dst_folder=cmd_args["output_path"])
    dump_dicom_all_tags(dicom_paths=dicom_paths, dst_folder=cmd_args["dump_path"])

    logger.info(f"{MODULE} finished: ({time.perf_counter() - timer:0.2f} seconds)")


if __name__ == "__main__":
    logger = init_logger(log_name=MODULE)
    cmd_args = parse_cmd_args()
    run_pipeline()
