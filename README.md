# Visual Regression Detection and Test Generation

Detects UI regressions from a code
change and generates a failing test that reproduces them. Given a user's design
intent, the app's design language, and before/after screenshots with bounding boxes, it flags
whether a change is a regression, localizes it, and writes a
test that fails on the regressed version.

## Approach
1. Collect design language and design intent for the change 
2. Capture before and after screenshots
3. Image-diff to produce candidate bounding boxes
4. Classify regression vs. intended change through a stateless LLM API call
5. If a regression is detected, a CLI agent inspects the codebase and generates a failing test

## PrairieLearn screenshot capture

`capture_screenshots.sh` accepts a PrairieLearn checkout and one of
three commands. `before` asks GitHub Copilot CLI to generate a focused
Playwright E2E spec from the component path and capture instructions. It always
creates a new spec, even if related tests exist; it may inspect them for
conventions but will not modify or reuse them. It runs the new spec and asks
Copilot to repair it when a run fails, retrying up to five test runs. `after`
reruns the selected spec without automatic repair.
`pr` publishes the before/after screenshots and DOM snapshots and creates a
draft PR.

```sh
./capture_screenshots.sh /path/to/PrairieLearn before \
  --component apps/prairielearn/src/components/example.tsx \
  --instructions "Open the student homepage as an enrolled student and capture the Example card."
./capture_screenshots.sh /path/to/PrairieLearn after
./capture_screenshots.sh /path/to/PrairieLearn pr
```

Screenshot and snapshot artifacts are saved under `.artifacts/` next to the
script. New specs are kept in
`apps/prairielearn/src/tests/e2e/generated-captures/` in the PrairieLearn
checkout. `before` creates a new spec each time it is run; use the same
`--name` on `after` and `pr` that was used for `before`. Use distinct names
when capturing multiple components with the same filename. The `pr` command
requires a pushed non-`master` branch and `gh` authentication. Capturing
requires GitHub Copilot CLI with authentication configured, Node.js 24+, pnpm
(or Corepack), and the normal local PrairieLearn E2E prerequisites.

## Attribution
- Element matching is adapted from Similo (Nass et al., 2023).
- Explaining changed pixels with the DOM is adapted from WebSee (Mahajan & Halfond, 2015).
- The example pages in `image_diff/examples/` are re-rendered from [WUICC](https://huggingface.co/datasets/zhangsan11111122/WUICC), which is built on [WebSight](https://huggingface.co/datasets/HuggingFaceM4/WebSight). Both are [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
