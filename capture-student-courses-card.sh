#!/usr/bin/env bash
set -euo pipefail

# Edit these defaults for the PR being documented.
PR_TITLE="Update the Student Courses Card"
PR_SUMMARY="Update the Student Courses Card."
PR_TESTING="Captured the Student Courses Card screenshot and DOM snapshot with the focused Playwright E2E spec."

prompt_for_pr_summary() {
  local default_summary="$1"
  local response

  printf 'Describe the change for the PR summary: '
  IFS= read -r response
  if [[ -n "$response" ]]; then
    PR_SUMMARY="$response"
  else
    PR_SUMMARY="$default_summary"
  fi
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PRAIRIELEARN_ROOT="$(cd -- "$SCRIPT_DIR/../PrairieLearn" && pwd)"
ARTIFACT_DIR="${ARTIFACT_DIR:-$PRAIRIELEARN_ROOT/.artifacts/student-courses-card}"
PR_IMAGE_DIR="${PR_IMAGE_DIR:-$PRAIRIELEARN_ROOT/.github/pr-images/student-courses-card}"
PR_IMAGE_PATH=".github/pr-images/student-courses-card"
PR_BODY_FILE="${PR_BODY_FILE:-$PRAIRIELEARN_ROOT/.github/pr-images/student-courses-card/pr-description.md}"
CAPTURE_TEST="src/tests/e2e/captureStudentCoursesScreenshots.spec.ts"
PNPM_VERSION="11.19.0"

usage() {
  printf 'Usage: %s before|after\n' "${0##*/}" >&2
  printf '  before  Capture the unchanged UI before editing it.\n' >&2
  printf '  after   Capture the changed UI and create a PrairieLearn draft PR to master.\n' >&2
}

if [[ $# -eq 1 && ( "$1" == "--help" || "$1" == "-h" ) ]]; then
  usage
  exit 0
fi

if [[ $# -ne 1 || ( "$1" != "before" && "$1" != "after" ) ]]; then
  usage
  exit 2
fi

if ! command -v node >/dev/null 2>&1; then
  printf 'Node.js >=24 is required by PrairieLearn, but node was not found on PATH.\n' >&2
  exit 1
fi
node_major="$(node -p 'Number(process.versions.node.split(".")[0])')"
if (( node_major < 24 )); then
  printf 'PrairieLearn requires Node.js >=24; found %s. Activate a compatible Node.js runtime and retry.\n' "$(node --version)" >&2
  exit 1
fi

if command -v pnpm >/dev/null 2>&1; then
  PNPM=(pnpm)
elif command -v corepack >/dev/null 2>&1; then
  PNPM=(corepack "pnpm@$PNPM_VERSION")
else
  printf 'pnpm was not found, and Corepack is unavailable. Install Corepack or pnpm %s, then retry.\n' "$PNPM_VERSION" >&2
  exit 1
fi

stage="$1"
mkdir -p "$ARTIFACT_DIR"

origin_url="$(git -C "$PRAIRIELEARN_ROOT" remote get-url origin)"
case "$origin_url" in
  https://github.com/*) pr_repo="${origin_url#https://github.com/}" ;;
  git@github.com:*) pr_repo="${origin_url#git@github.com:}" ;;
  ssh://git@github.com/*) pr_repo="${origin_url#ssh://git@github.com/}" ;;
  *)
    printf 'PrairieLearn origin must be a GitHub repository URL; got: %s\n' "$origin_url" >&2
    exit 1
    ;;
esac
pr_repo="${pr_repo%.git}"

if [[ "${pr_repo##*/}" != "PrairieLearn" ]]; then
  printf 'Expected PrairieLearn origin, got %s. Refusing to create a PR.\n' "$pr_repo" >&2
  exit 1
fi

if [[ "$stage" == "after" ]]; then
  for before_artifact in before.png before_snapshot.json; do
    if [[ ! -f "$ARTIFACT_DIR/$before_artifact" ]]; then
      printf 'Missing %s. Run the before stage before editing the UI.\n' "$ARTIFACT_DIR/$before_artifact" >&2
      exit 1
    fi
  done
fi

if [[ "$stage" == "after" ]]; then
  if ! command -v gh >/dev/null 2>&1; then
    printf 'GitHub CLI (gh) is required to create the draft PR.\n' >&2
    exit 1
  fi

  pr_branch="$(git -C "$PRAIRIELEARN_ROOT" branch --show-current)"
  if [[ -z "$pr_branch" || "$pr_branch" == "master" ]]; then
    printf 'Check out a non-master PrairieLearn branch before creating the PR.\n' >&2
    exit 1
  fi

  local_head="$(git -C "$PRAIRIELEARN_ROOT" rev-parse HEAD)"
  remote_head="$(git -C "$PRAIRIELEARN_ROOT" ls-remote --heads origin "refs/heads/$pr_branch" | cut -f1)"
  if [[ "$local_head" != "$remote_head" ]]; then
    printf 'Push the current PrairieLearn branch (%s) to origin before creating its PR.\n' "$pr_branch" >&2
    exit 1
  fi
fi

(
  cd "$PRAIRIELEARN_ROOT"
  CAPTURE_SCREENSHOTS=1 \
    OUT_DIR="$ARTIFACT_DIR" \
    "${PNPM[@]}" --filter @prairielearn/prairielearn test:e2e "$CAPTURE_TEST"
)

captured_image="$ARTIFACT_DIR/student-courses-card.png"
captured_snapshot="$ARTIFACT_DIR/student-courses-card_snapshot.json"
if [[ ! -f "$captured_image" ]]; then
  printf 'Expected screenshot was not created: %s\n' "$captured_image" >&2
  exit 1
fi
if [[ ! -f "$captured_snapshot" ]]; then
  printf 'Expected DOM snapshot was not created: %s\n' "$captured_snapshot" >&2
  exit 1
fi

cp "$captured_image" "$ARTIFACT_DIR/$stage.png"
printf 'Saved %s screenshot: %s\n' "$stage" "$ARTIFACT_DIR/$stage.png"
cp "$captured_snapshot" "$ARTIFACT_DIR/${stage}_snapshot.json"
printf 'Saved %s DOM snapshot: %s\n' "$stage" "$ARTIFACT_DIR/${stage}_snapshot.json"

if [[ "$stage" == "after" ]]; then
  prompt_for_pr_summary "$PR_SUMMARY"

  mkdir -p "$PR_IMAGE_DIR"
  cp -f "$ARTIFACT_DIR/before.png" "$PR_IMAGE_DIR/before.png"
  cp -f "$ARTIFACT_DIR/after.png" "$PR_IMAGE_DIR/after.png"
  cp -f "$ARTIFACT_DIR/before_snapshot.json" "$PR_IMAGE_DIR/before_snapshot.json"
  cp -f "$ARTIFACT_DIR/after_snapshot.json" "$PR_IMAGE_DIR/after_snapshot.json"

  before_url="https://raw.githubusercontent.com/${pr_repo}/${pr_branch}/${PR_IMAGE_PATH}/before.png"
  after_url="https://raw.githubusercontent.com/${pr_repo}/${pr_branch}/${PR_IMAGE_PATH}/after.png"
  before_snapshot_url="https://raw.githubusercontent.com/${pr_repo}/${pr_branch}/${PR_IMAGE_PATH}/before_snapshot.json"
  after_snapshot_url="https://raw.githubusercontent.com/${pr_repo}/${pr_branch}/${PR_IMAGE_PATH}/after_snapshot.json"

  (
    cd "$PRAIRIELEARN_ROOT"
    git add \
      "$PR_IMAGE_PATH/before.png" \
      "$PR_IMAGE_PATH/after.png" \
      "$PR_IMAGE_PATH/before_snapshot.json" \
      "$PR_IMAGE_PATH/after_snapshot.json"
    if ! git diff --cached --quiet --exit-code; then
      git commit -m "Add Student Courses Card screenshots for PR review"
      git push origin "$pr_branch"
    fi
  )

  pr_owner="${pr_repo%%/*}"
  cat > "$PR_BODY_FILE" <<EOF
# Description

$PR_SUMMARY

## Screenshots

| Before | After |
| --- | --- |
| ![Before]($before_url) | ![After]($after_url) |

## DOM Snapshots

- [Before]($before_snapshot_url)
- [After]($after_snapshot_url)

## Testing

$PR_TESTING

- [ ] I have disclosed the level of AI assistance used (i.e. none, specific portions, majority of implementation).
EOF
  printf 'Generated PR description draft: %s\n' "$PR_BODY_FILE"

  pr_url="$(gh pr create \
    --repo "$pr_repo" \
    --base master \
    --head "$pr_owner:$pr_branch" \
    --draft \
    --title "$PR_TITLE" \
    --body-file "$PR_BODY_FILE")"
  printf 'Created draft PR: %s\n' "$pr_url"
  printf 'Screenshot and DOM snapshot assets live in %s.\n' "$PR_IMAGE_DIR"
fi