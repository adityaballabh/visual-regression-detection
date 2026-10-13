"""Capture before/after UI screenshots and create a draft PrairieLearn PR."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ARTIFACT_ROOT = SCRIPT_DIR / ".artifacts"
E2E_DIR = Path("apps/prairielearn/src/tests/e2e")
PNPM_VERSION = "11.19.0"
MAX_SPEC_ATTEMPTS = 5


class CaptureError(Exception):
    """An expected failure with a concise command-line error."""


def run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            text=True,
            check=False,
            capture_output=capture_output,
        )
    except FileNotFoundError as error:
        raise CaptureError(f"Required command not found: {command[0]}") from error
    if result.returncode:
        detail = ""
        if capture_output:
            detail = "\n".join(
                part.strip() for part in (result.stdout, result.stderr) if part.strip()
            )
        message = f"Command failed ({result.returncode}): {' '.join(command)}"
        if detail:
            message += f"\n{detail}"
        raise CaptureError(message)
    return result


def slugify(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", value)
    value = re.sub(r"([A-Z])([A-Z][a-z])", r"\1-\2", value)
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise CaptureError("The capture name must contain at least one letter or number.")
    return slug


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a focused Playwright spec, capture before/after screenshots "
        "and DOM snapshots, and optionally create a draft PR."
    )
    parser.add_argument("prairielearn_root", type=Path, help="Path to the PrairieLearn repo")
    parser.add_argument("command", choices=("before", "after", "pr"))
    parser.add_argument(
        "--component",
        help="Component source file, relative to the repo root (required for before)",
    )
    parser.add_argument(
        "--instructions",
        help="Page state, target element, and setup details for the generated spec",
    )
    parser.add_argument(
        "--name",
        help="Capture name; defaults to the component filename for before, "
        "and selects a capture for after/pr",
    )
    parser.add_argument("--title", help="Optional pull request title")
    return parser.parse_args()


def resolve_root(root_arg: Path) -> Path:
    root = root_arg.expanduser().resolve()
    if not (root / "package.json").is_file() or not (root / E2E_DIR / "fixtures.ts").is_file():
        raise CaptureError(
            f"{root} does not look like a PrairieLearn checkout "
            f"(expected package.json and {E2E_DIR / 'fixtures.ts'})."
        )
    return root


def capture_key(root: Path, component: Path, instructions: str, name: str) -> str:
    value = f"{root}\0{component}\0{instructions}\0{name}"
    return hashlib.sha256(value.encode()).hexdigest()[:10]


def artifact_dir(root: Path, component: Path, instructions: str, name: str) -> Path:
    return ARTIFACT_ROOT / f"{name}-{capture_key(root, component, instructions, name)}"


def spec_path(root: Path, name: str, key: str) -> Path:
    return root / E2E_DIR / "generated-captures" / f"capture-{name}-{key}.spec.ts"


def run_agent(prompt: str, *, root: Path) -> str:
    copilot = shutil.which("copilot")
    if not copilot:
        raise CaptureError("Copilot CLI is required to prepare a capture spec, but was not found.")
    result = run(
        [copilot, "-p", prompt, "--allow-tool=write"],
        cwd=root,
        capture_output=True,
    )
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")
    return result.stdout


def resolve_selected_spec(
    root: Path, response: str, expected_new_spec: Path
) -> Path:
    path_matches = re.findall(r"^CAPTURE_SPEC_PATH:\s*(.+?)\s*$", response, re.MULTILINE)
    if not path_matches:
        raise CaptureError(
            "Copilot did not report the new spec path. "
            "Review its output and rerun before."
        )
    selected = Path(path_matches[-1])
    selected = selected.resolve() if selected.is_absolute() else (root / selected).resolve()
    e2e_root = (root / E2E_DIR).resolve()
    try:
        selected.relative_to(e2e_root)
    except ValueError as error:
        raise CaptureError(f"Selected spec must be inside {e2e_root}: {selected}") from error
    if selected.suffix != ".ts" or not selected.name.endswith(".spec.ts"):
        raise CaptureError(f"Selected capture file must be a Playwright .spec.ts file: {selected}")
    if not selected.is_file() or selected.stat().st_size == 0:
        raise CaptureError(f"Copilot selected a spec that does not exist or is empty: {selected}")
    if selected != expected_new_spec.resolve():
        raise CaptureError(
            f"Copilot must create the requested new spec at {expected_new_spec}, "
            f"not select or reuse {selected}."
        )
    return selected


def prepare_spec(
    root: Path,
    component: Path,
    instructions: str,
    name: str,
    key: str,
) -> Path:
    destination = spec_path(root, name, key)
    destination.parent.mkdir(parents=True, exist_ok=True)
    screenshot_name = f"{name}.png"
    snapshot_name = f"{name}_snapshot.json"
    prompt = f"""Create a new, standalone PrairieLearn Playwright E2E capture spec.

Component source: {root / component}
Capture name: {name}
Capture instructions: {instructions}
Create this new file: {destination}

Always create the specified new spec, even if related capture specs or tests
already exist. Do not reuse, edit, or add tests to an existing file. You may
inspect existing specs for conventions and fixture usage, but do not modify
them. Use PrairieLearn's existing fixtures and conventions for the required
user, page, and data. If essential details cannot be inferred, do not invent
fragile selectors or test data; report the ambiguity.

The spec must be skipped unless CAPTURE_SCREENSHOTS=1, and write both files
directly into the absolute directory supplied in process.env.OUT_DIR:
- {screenshot_name}
- {snapshot_name}
Capture the requested element/page as a PNG and a Chromium DOMSnapshot JSON
including computed styles, device pixel ratio, and paint order. Create OUT_DIR
if needed. Use PrairieLearn's existing E2E fixtures for its app server, test
database, and test course.

Only create the specified new spec. Do not modify any existing files or other
files, change repository state, commit, push, or create a pull request. Do not
create screenshots; the caller will run this spec.

After preparing the spec, print exactly one machine-readable line containing
the newly created spec's path relative to the PrairieLearn repository:
CAPTURE_SPEC_PATH: apps/prairielearn/src/tests/e2e/relative-file.spec.ts
"""
    print(f"Generating a new Playwright capture spec in {root / E2E_DIR}")
    response = run_agent(prompt, root=root)
    selected = resolve_selected_spec(root, response, destination)
    print(f"Using new Playwright capture spec: {selected.relative_to(root)}")
    source = selected.read_text(encoding="utf-8")
    if (
        screenshot_name not in source
        or snapshot_name not in source
        or "CAPTURE_SCREENSHOTS" not in source
    ):
        raise CaptureError(
            f"Selected spec must be gated by CAPTURE_SCREENSHOTS and write "
            f"{screenshot_name} and {snapshot_name}; review or correct the spec before retrying."
        )
    return selected


def select_pnpm() -> list[str]:
    if shutil.which("pnpm"):
        return ["pnpm"]
    if shutil.which("corepack"):
        return ["corepack", f"pnpm@{PNPM_VERSION}"]
    raise CaptureError(
        f"pnpm was not found and Corepack is unavailable. Install Corepack or pnpm {PNPM_VERSION}."
    )


def capture_command(root: Path, spec: Path, output_dir: Path) -> tuple[list[str], dict[str, str]]:
    node = shutil.which("node")
    if not node:
        raise CaptureError("Node.js >=24 is required by PrairieLearn, but node was not found on PATH.")
    major = run(
        [node, "-p", "Number(process.versions.node.split('.')[0])"],
        cwd=root,
        capture_output=True,
    )
    if int(major.stdout.strip()) < 24:
        version = run([node, "--version"], cwd=root, capture_output=True).stdout.strip()
        raise CaptureError(f"PrairieLearn requires Node.js >=24; found {version}.")

    app_root = root / "apps/prairielearn"
    try:
        relative_spec = spec.relative_to(app_root)
    except ValueError as error:
        raise CaptureError(f"Capture spec must live in the PrairieLearn app: {spec}") from error

    output_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["CAPTURE_SCREENSHOTS"] = "1"
    env["OUT_DIR"] = str(output_dir)
    command = [
        *select_pnpm(),
        "--filter",
        "@prairielearn/prairielearn",
        "test:e2e",
        relative_spec.as_posix(),
    ]
    return command, env


def run_capture_attempt(
    root: Path, spec: Path, output_dir: Path, name: str
) -> str | None:
    command, env = capture_command(root, spec, output_dir)
    for filename in (f"{name}.png", f"{name}_snapshot.json"):
        (output_dir / filename).unlink(missing_ok=True)
    try:
        result = subprocess.run(
            command,
            cwd=root,
            env=env,
            text=True,
            check=False,
            capture_output=True,
        )
    except FileNotFoundError as error:
        raise CaptureError(f"Required command not found: {command[0]}") from error

    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    if output:
        print(output, end="" if output.endswith("\n") else "\n")
    if result.returncode:
        return f"E2E command failed with exit code {result.returncode}.\n{output}"

    missing = [
        filename
        for filename in (f"{name}.png", f"{name}_snapshot.json")
        if not (output_dir / filename).is_file()
    ]
    if missing:
        return "E2E test passed but did not create required output files: " + ", ".join(missing)
    return None


def run_capture(root: Path, spec: Path, output_dir: Path, name: str) -> None:
    failure = run_capture_attempt(root, spec, output_dir, name)
    if failure:
        raise CaptureError(failure)


def repair_spec(
    root: Path,
    spec: Path,
    component: Path,
    instructions: str,
    name: str,
    failure: str,
    attempt: int,
) -> None:
    prompt = f"""Repair the existing PrairieLearn Playwright capture spec so its
focused E2E run passes and produces the required screenshot and DOM snapshot.

Spec to edit (the only file you may modify): {spec}
Component source: {root / component}
Capture name: {name}
Capture instructions: {instructions}
Screenshot required in process.env.OUT_DIR: {name}.png
DOM snapshot required in process.env.OUT_DIR: {name}_snapshot.json

This is repair attempt {attempt} after the previous E2E run failed. Diagnose
the failure output below. Fix the underlying test/spec issue without weakening
the intended capture, removing meaningful assertions, or changing unrelated
files. Edit only this selected spec; do not add another complete test or
repurpose a spec for a different TSX component. Preserve PrairieLearn's existing fixtures and keep the
CAPTURE_SCREENSHOTS=1 guard. Do not run commands, modify other files, commit,
push, or create a pull request; the caller will rerun the test.

Failure output:
{failure[-20000:]}
"""
    print(f"Asking Copilot to repair the capture spec (retry {attempt})")
    run_agent(prompt, root=root)


def capture_until_passes(
    root: Path,
    spec: Path,
    output_dir: Path,
    component: Path,
    instructions: str,
    name: str,
) -> None:
    for attempt in range(1, MAX_SPEC_ATTEMPTS + 1):
        print(f"Running capture E2E test (attempt {attempt}/{MAX_SPEC_ATTEMPTS})")
        failure = run_capture_attempt(root, spec, output_dir, name)
        if failure is None:
            return
        if attempt == MAX_SPEC_ATTEMPTS:
            raise CaptureError(
                f"Capture spec did not pass after {MAX_SPEC_ATTEMPTS} attempts.\n{failure}"
            )
        repair_spec(
            root,
            spec,
            component,
            instructions,
            name,
            failure,
            attempt,
        )


def read_capture_manifest(
    directory: Path, root: Path, *, require_spec: bool = True
) -> dict[str, str]:
    manifest = directory / "capture.json"
    if not manifest.is_file():
        raise CaptureError("No matching capture has been initialized. Run before first.")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CaptureError(f"Could not read capture metadata: {manifest}") from error
    if data.get("prairielearn_root") != str(root):
        raise CaptureError("Capture metadata belongs to a different PrairieLearn checkout.")
    spec = root / data.get("spec_path", "")
    if require_spec and not spec.is_file():
        raise CaptureError(f"Generated capture spec is missing: {spec}")
    data["resolved_spec_path"] = str(spec)
    return data


def find_capture(root: Path, requested_name: str | None) -> Path:
    matches: list[Path] = []
    if ARTIFACT_ROOT.is_dir():
        for manifest in ARTIFACT_ROOT.glob("*/capture.json"):
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise CaptureError(f"Could not read capture metadata: {manifest}") from error
            if data.get("prairielearn_root") != str(root):
                continue
            if requested_name and data.get("name") != requested_name:
                continue
            matches.append(manifest.parent)
    if not matches:
        raise CaptureError("No matching capture found. Run before first or supply its --name.")
    if len(matches) > 1:
        raise CaptureError("More than one capture matches; supply --name to select one.")
    return matches[0]


def save_stage(directory: Path, name: str, stage: str) -> None:
    shutil.copy2(directory / f"{name}.png", directory / f"{stage}.png")
    shutil.copy2(directory / f"{name}_snapshot.json", directory / f"{stage}_snapshot.json")
    print(f"Saved {stage} screenshot: {directory / f'{stage}.png'}")
    print(f"Saved {stage} DOM snapshot: {directory / f'{stage}_snapshot.json'}")


def do_before(root: Path, component: Path, instructions: str, name: str) -> None:
    key = capture_key(root, component, instructions, name)
    directory = artifact_dir(root, component, instructions, name)
    capture_manifest = directory / "capture.json"
    spec_id = f"{key}-{uuid.uuid4().hex[:8]}"
    selected_spec = prepare_spec(root, component, instructions, name, spec_id)

    directory.mkdir(parents=True, exist_ok=True)
    data = {
        "prairielearn_root": str(root),
        "component": component.as_posix(),
        "instructions": instructions,
        "name": name,
        "spec_path": selected_spec.relative_to(root).as_posix(),
    }
    capture_manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    capture_until_passes(root, selected_spec, directory, component, instructions, name)
    save_stage(directory, name, "before")


def do_after(root: Path, directory: Path) -> None:
    data = read_capture_manifest(directory, root)
    name = data["name"]
    for required in ("before.png", "before_snapshot.json"):
        if not (directory / required).is_file():
            raise CaptureError(f"Missing {directory / required}. Run before before after.")
    run_capture(root, Path(data["resolved_spec_path"]), directory, name)
    save_stage(directory, name, "after")


def git(root: Path, *args: str, capture_output: bool = True) -> str:
    result = run(["git", *args], cwd=root, capture_output=capture_output)
    return result.stdout.strip() if capture_output else ""


def github_repo(root: Path) -> str:
    origin = git(root, "remote", "get-url", "origin")
    match = re.search(
        r"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([^/]+/[^/]+?)(?:\.git)?$",
        origin,
    )
    if not match:
        raise CaptureError(f"origin must be a GitHub repository URL; got: {origin}")
    return match.group(1)


def do_pr(root: Path, directory: Path, title_override: str) -> None:
    data = read_capture_manifest(directory, root)
    name = data["name"]
    repo = github_repo(root)
    if not shutil.which("gh"):
        raise CaptureError("GitHub CLI (gh) is required to create the draft PR.")
    for required in ("before.png", "after.png", "before_snapshot.json", "after_snapshot.json"):
        if not (directory / required).is_file():
            raise CaptureError(f"Missing {directory / required}. Run before and after first.")

    branch = git(root, "branch", "--show-current")
    if not branch or branch == "master":
        raise CaptureError("Check out a non-master PrairieLearn branch before creating the PR.")
    local_head = git(root, "rev-parse", "HEAD")
    remote_head = git(root, "ls-remote", "--heads", "origin", f"refs/heads/{branch}").split()
    if not remote_head or local_head != remote_head[0]:
        raise CaptureError(f"Push the current PrairieLearn branch ({branch}) to origin before creating the PR.")

    capture_title = name.replace("-", " ").title()
    title = title_override or f"Update the {capture_title}"
    default_summary = f"Update the {capture_title}."
    summary = input("Describe the change for the PR summary: ").strip() or default_summary
    image_path = Path(".github/pr-images") / name
    image_dir = root / image_path
    image_dir.mkdir(parents=True, exist_ok=True)
    assets = ("before.png", "after.png", "before_snapshot.json", "after_snapshot.json")
    for asset in assets:
        shutil.copy2(directory / asset, image_dir / asset)

    base_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{image_path.as_posix()}"
    before_url = f"{base_url}/before.png"
    after_url = f"{base_url}/after.png"
    before_snapshot_url = f"{base_url}/before_snapshot.json"
    after_snapshot_url = f"{base_url}/after_snapshot.json"
    asset_paths = [f"{image_path.as_posix()}/{asset}" for asset in assets]
    git(root, "add", *asset_paths, capture_output=False)
    changed = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--exit-code", "--", *asset_paths],
        cwd=root,
        check=False,
    )
    if changed.returncode not in (0, 1):
        raise CaptureError("Could not check staged screenshot assets.")
    if changed.returncode == 1:
        git(
            root,
            "commit",
            "-m",
            f"Add {capture_title} screenshots for PR review",
            "-m",
            "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>",
            "--",
            *asset_paths,
            capture_output=False,
        )
        git(root, "push", "origin", branch, capture_output=False)

    body_path = image_dir / "pr-description.md"
    body_path.write_text(
        f"""# Description

{summary}

## Screenshots

| Before | After |
| --- | --- |
| ![Before]({before_url}) | ![After]({after_url}) |

## DOM Snapshots

- [Before]({before_snapshot_url})
- [After]({after_snapshot_url})

## Testing

Captured the {capture_title} screenshot and DOM snapshot with the focused Playwright E2E spec.

- [ ] I have disclosed the level of AI assistance used (i.e. none, specific portions, majority of implementation).
""",
        encoding="utf-8",
    )
    print(f"Generated PR description draft: {body_path}")
    pr_url = run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            repo,
            "--base",
            "master",
            "--head",
            f"{repo.split('/')[0]}:{branch}",
            "--draft",
            "--title",
            title,
            "--body-file",
            str(body_path),
        ],
        cwd=root,
        capture_output=True,
    ).stdout.strip()
    print(f"Created draft PR: {pr_url}")
    print(f"Screenshot and DOM snapshot assets live in {image_dir}.")


def main() -> int:
    args = parse_args()
    try:
        root = resolve_root(args.prairielearn_root)
        if args.command == "before":
            if not args.component or not args.instructions:
                raise CaptureError("before requires --component and --instructions.")
            component_path = Path(args.component)
            component_path = (
                (root / component_path).resolve()
                if not component_path.is_absolute()
                else component_path.resolve()
            )
            try:
                component = component_path.relative_to(root)
            except ValueError as error:
                raise CaptureError("--component must refer to a file inside PrairieLearn.") from error
            if not component_path.is_file():
                raise CaptureError(f"Component file not found: {component_path}")
            instructions = args.instructions.strip()
            if not instructions:
                raise CaptureError("--instructions must not be empty.")
            name = slugify(args.name or component_path.stem)
            do_before(root, component, instructions, name)
        else:
            if args.component or args.instructions:
                raise CaptureError("--component and --instructions are only valid for before.")
            name = slugify(args.name) if args.name else None
            directory = find_capture(root, name)
            if args.command == "after":
                if args.title:
                    raise CaptureError("--title is only valid for pr.")
                do_after(root, directory)
            else:
                do_pr(root, directory, args.title or "")
    except CaptureError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
