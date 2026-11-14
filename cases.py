from pathlib import Path
from urllib.parse import urlparse

from github import Github
from github.Repository import Repository


def pr_repo(pr_url: str) -> tuple[Repository, int]:
    owner, repo, _, number = urlparse(pr_url).path.strip("/").split("/")[:4]
    return Github().get_repo(f"{owner}/{repo}"), int(number)


def diff_folder(case_folder: Path, variant: str) -> Path:
    return case_folder / "out" / ("pixel" if variant == "no_snapshots" else "dom")


def reports_folder(case_folder: Path, model: str, variant: str) -> Path:
    return case_folder / "out" / "regression_detection" / model / variant


def tests_folder(
    case_folder: Path, generator: Path, detection_model: str, detection_variant: str, detection_mode: str
) -> Path:
    detection = Path(f"detection-{detection_model}", detection_variant, detection_mode)
    return case_folder / "out" / "test_generation" / generator / detection
