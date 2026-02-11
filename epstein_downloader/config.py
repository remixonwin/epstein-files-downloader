"""Configuration and constants for the Epstein Files Downloader."""

from dataclasses import dataclass
from typing import Optional

# Required cookie for DOJ website
DOJ_COOKIE = "justiceGovAgeVerified=true"

# Base URLs
DOJ_BASE_URL = "https://www.justice.gov"
DOJ_FILES_URL = f"{DOJ_BASE_URL}/epstein/files"
DOJ_LISTING_URL = f"{DOJ_BASE_URL}/epstein/doj-disclosures"

# Archive.org trackers for torrents
TRACKERS = [
    "http://bt1.archive.org:6969/announce",
    "http://bt2.archive.org:6969/announce",
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://tracker.openbittorrent.com:6969/announce",
    "udp://9.rarbg.com:2810/announce",
    "udp://explodie.org:6969/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://tracker.moeking.me:6969/announce",
    "udp://open.stealth.si:80/announce",
    "udp://vibe.community:6969/announce",
]


@dataclass
class DatasetInfo:
    """Information about a dataset."""
    number: int
    zip_available: bool
    zip_size_mb: Optional[int]
    magnet: Optional[str]
    magnet_size_gb: Optional[float]
    efta_start: Optional[int]
    efta_end: Optional[int]
    checksum_sha256: Optional[str] = None
    checksum_md5: Optional[str] = None


# Dataset configurations
DATASETS = {
    1: DatasetInfo(
        number=1,
        zip_available=True,
        zip_size_mb=1260,
        magnet=None,
        magnet_size_gb=None,
        efta_start=1,
        efta_end=39024,
    ),
    2: DatasetInfo(
        number=2,
        zip_available=True,
        zip_size_mb=631,
        magnet=None,
        magnet_size_gb=None,
        efta_start=None,
        efta_end=None,
    ),
    3: DatasetInfo(
        number=3,
        zip_available=True,
        zip_size_mb=595,
        magnet=None,
        magnet_size_gb=None,
        efta_start=None,
        efta_end=None,
    ),
    4: DatasetInfo(
        number=4,
        zip_available=True,
        zip_size_mb=352,
        magnet=None,
        magnet_size_gb=None,
        efta_start=None,
        efta_end=None,
    ),
    5: DatasetInfo(
        number=5,
        zip_available=True,
        zip_size_mb=61,
        magnet=None,
        magnet_size_gb=None,
        efta_start=None,
        efta_end=None,
    ),
    6: DatasetInfo(
        number=6,
        zip_available=True,
        zip_size_mb=51,
        magnet=None,
        magnet_size_gb=None,
        efta_start=None,
        efta_end=None,
    ),
    7: DatasetInfo(
        number=7,
        zip_available=True,
        zip_size_mb=97,
        magnet=None,
        magnet_size_gb=None,
        efta_start=None,
        efta_end=None,
    ),
    8: DatasetInfo(
        number=8,
        zip_available=True,
        zip_size_mb=10200,
        magnet=None,
        magnet_size_gb=None,
        efta_start=None,
        efta_end=None,
    ),
    9: DatasetInfo(
        number=9,
        zip_available=False,  # REMOVED!
        zip_size_mb=None,
        magnet="magnet:?xt=urn:btih:0a3d4b84a77bd982c9c2761f40944402b94f9c64",
        magnet_size_gb=46,  # Partial
        efta_start=39025,
        efta_end=1262781,
    ),
    10: DatasetInfo(
        number=10,
        zip_available=False,  # REMOVED!
        zip_size_mb=None,
        magnet="magnet:?xt=urn:btih:d509cc4ca1a415a9ba3b6cb920f67c44aed7fe1f",
        magnet_size_gb=82,
        efta_start=1262782,
        efta_end=2205654,
        checksum_sha256="7D6935B1C63FF2F6BCABDD024EBC2A770F90C43B0D57B646FA7CBD4C0ABCF846",
        checksum_md5="B8A72424AE812FD21D225195812B2502",
    ),
    11: DatasetInfo(
        number=11,
        zip_available=False,  # REMOVED!
        zip_size_mb=None,
        magnet=None,  # No verified magnet yet
        magnet_size_gb=None,
        efta_start=2205655,
        efta_end=2730264,
    ),
    12: DatasetInfo(
        number=12,
        zip_available=True,
        zip_size_mb=114,
        magnet="magnet:?xt=urn:btih:8bc781c7259f4b82406cd2175a1d5e9c3b6bfc90",
        magnet_size_gb=0.114,
        efta_start=2730265,
        efta_end=None,
    ),
}


def get_zip_url(dataset_num: int) -> str:
    """Get the ZIP download URL for a dataset."""
    return f"{DOJ_FILES_URL}/DataSet%20{dataset_num}.zip"


def get_pdf_url(dataset_num: int, efta_num: int) -> str:
    """Get the PDF URL for a specific EFTA number."""
    return f"{DOJ_FILES_URL}/DataSet%20{dataset_num}/EFTA{efta_num:08d}.pdf"


def get_listing_url(dataset_num: int, page: int = 0) -> str:
    """Get the file listing page URL."""
    return f"{DOJ_LISTING_URL}/data-set-{dataset_num}-files?page={page}"


def get_magnet_with_trackers(magnet: str) -> str:
    """Add trackers to a magnet link."""
    if not magnet:
        return magnet
    tracker_params = "&".join(f"tr={t}" for t in TRACKERS)
    if "?" in magnet:
        return f"{magnet}&{tracker_params}"
    return f"{magnet}?{tracker_params}"
