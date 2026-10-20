# Visual Regression Detection and Test Generation

Detects UI regressions from a code
change and generates a failing test that reproduces them. Given a user's design
intent, the app's design language, and before/after screenshots with bounding boxes, it flags
whether a change is a regression, localizes it, and writes a
test that fails on the regressed version.

## Pipeline
1. Collect design language and design intent for the change 
2. Capture before and after screenshots
3. Image-diff to produce candidate bounding boxes
4. Classify regression vs. intended change through a stateless LLM API call
5. If a regression is detected, a CLI agent inspects the codebase and generates a failing test

## Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

Copy [`.env.example`](.env.example) to `.env` and add your Gemini API key.

Run all commands from the repository root.

## Run
[`pipeline.py`](pipeline.py) runs steps 2 to 4 on one case folder:
```bash
python pipeline.py <case_folder> [--llm-input dom|pixel] [--llm-mode context|baseline|both] [--llm-dry-run]
```

A case folder holds one change:
```
<case_folder>/
  html/       before.html and after.html (optional)
  pr.txt      link to a PrairieLearn PR made by the capture script (optional)
  captures/   before.png, after.png and their _snapshot.json files (if missing, generated from html/ or pr.txt)
  design/     design_intent.md and design_language.md (optional)
  out/        written by the pipeline: dom/ and pixel/ for the image diff, llm/ for the reports
```

If `captures/` is incomplete, the pipeline fills it. For a PrairieLearn change, put the link to the PR made by the [PrairieLearn screenshot capture](#prairielearn-screenshot-capture) in `pr.txt`, and the pipeline downloads the captures committed in that PR. For any other page, put the before and after HTML in `html/`, and the pipeline captures them itself. `--llm-dry-run` prints the LLM prompt without calling Gemini. `--llm-input` picks which diff the LLM reads, `dom` by default.

### Examples
Each folder in [`examples/general/`](examples/general/) is a case.

To update every example's `out/` after a code change, run [`examples/update_outputs.py`](examples/update_outputs.py):
```bash
python -m examples.update_outputs [--llm-dry-run]
```

The example pages are re-rendered from [WUICC](https://huggingface.co/datasets/zhangsan11111122/WUICC), which is built on [WebSight](https://huggingface.co/datasets/HuggingFaceM4/WebSight), and the synthetic ones use text from WUICC pages. WUICC and WebSight are both [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## PrairieLearn screenshot capture

[`prairielearn_capture/capture_screenshots.sh`](prairielearn_capture/capture_screenshots.sh) accepts a PrairieLearn checkout and one of
three commands. `before` asks GitHub Copilot CLI to generate a focused
Playwright E2E spec from the component path and capture instructions. It always
creates a new spec, even if related tests exist; it may inspect them for
conventions but will not modify or reuse them. It runs the new spec and asks
Copilot to repair it when a run fails, retrying up to five test runs. `after`
reruns the selected spec without automatic repair.
`pr` publishes the before/after screenshots and DOM snapshots and creates a
draft PR.

Generated specs use PrairieLearn's shared E2E snapshot helper so screenshots
and DOM snapshots use the same viewport, wait for fonts and MathJax, freeze
animations, and serialize computed styles in the normalized format consumed by
`image_diff`.

```sh
./prairielearn_capture/capture_screenshots.sh /path/to/PrairieLearn before \
  --component apps/prairielearn/src/components/example.tsx \
  --instructions "Open the student homepage as an enrolled student and capture the Example card."
./prairielearn_capture/capture_screenshots.sh /path/to/PrairieLearn after
./prairielearn_capture/capture_screenshots.sh /path/to/PrairieLearn pr
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

## Image diff

### Run
```bash
python -m image_diff <before_image> <after_image> --out <path> --before-snapshot <before_snapshot> --after-snapshot <after_snapshot>
```

### Approach
A simple pixel diff boxes everything a change moves, so if an element grows, everything below it gets a box. Instead, our image diff uses the DOM to report just that element, with what changed and how far it pushed the rest.

1. Pixel diff\
   Boxes pixels that changed color (Delta E > 3 in Lab) or shape (Canny edges).
2. Element matching ([Similo](https://doi.org/10.1145/3571855), Nass et al., 2023)\
   Pairs each element on the before page with its match on the after page.
3. Causes ([X-PERT](https://doi.org/10.1109/ICSE.2013.6606616), Choudhary, Prasad & Orso, 2013)\
   Finds the size, spacing and added, removed or reordered elements that changed the layout, and records how far each one pushed the rest.
4. Box labeling ([WebSee](https://doi.org/10.1109/ICST.2015.7102586), Mahajan & Halfond, 2015)\
   Matches each box to the changed element it covers, and drops boxes that only contain moved content.
5. Unexplained boxes\
   If no cause explains a box, like a replaced image, the box is still kept.

## LLM-based regression detection

The script is [`llm/gemini_processor.py`](llm/gemini_processor.py).

It takes the image diff output folder of a case, like [`examples/general/button_enlarged/out/dom`](examples/general/button_enlarged/out/dom).

That folder contains `before_color.png`, `after_color.png`, `before_shape.png`, `after_shape.png` and `boxes.json`. [`pipeline.py`](pipeline.py) also passes `design_intent.md` and `design_language.md` from the case's `design/` folder if it exists.

### Run and Operation 

To do a dry run (without calling Gemini, checking inputs): 
```
python llm/gemini_processor.py run "folder-containing-images" --mode both --dry-run
```
To do a complete run (calling Gemini): 
```
python llm/gemini_processor.py run "folder-containing-images" --mode both
```

### Parameters
`--mode` takes three values: `both`, `baseline`, `context`

Both runs both baseline and context

Baseline takes in only the 4 images + boxes.json without any design context. 

Context takes in the 4 images + boxes.json + PR link, design context and intent. 
