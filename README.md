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
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

Captures use your installed Chrome.

Copy [`.env.example`](.env.example) to `.env` and add your Gemini API key.

Run all commands from the repository root.

## Run
[`pipeline.py`](pipeline.py) runs the first 4 steps on one case folder:
```bash
python pipeline.py <case_folder> [--detection-variant all|images|boxes|no_snapshots] [--detection-model MODEL] [--detection-mode context|baseline|both] [--detection-dry-run]
```

A case folder holds one change:
```
<case_folder>/
  html/       before.html and after.html (optional)
  pr.txt      link to a PrairieLearn PR made by the capture script (optional)
  captures/   before.png, after.png and their _snapshot.json files (if missing, generated from html/ or pr.txt)
  design/     design_intent.md and design_language.md (optional, pulled from pr.txt if missing)
  out/        written by the pipeline: dom/ and pixel/ for the image diff, regression_detection/<model>/<variant>/ for the reports
```

If `captures/` is incomplete, the pipeline fills it. For a PrairieLearn change, put the link to the PR made by the [PrairieLearn screenshot capture](#prairielearn-screenshot-capture) in `pr.txt`, and the pipeline downloads the captures committed in that PR. Missing design files come from the PR too: the intent from its description and the design language from the PrairieLearn fork's `docs/design-standards.md`. For any other page, put the before and after HTML in `html/`, and the pipeline captures them itself.

`--detection-variant` picks what the LLM gets:
- `all` (default): annotated images and `boxes.json`
- `images`: annotated images only
- `boxes`: `boxes.json` only
- `no_snapshots`: annotated images and `boxes.json` from the pixel-only diff

`--detection-model` picks the Gemini model. `--detection-mode` picks the context prompt, the baseline prompt or both (`context` by default). `--detection-dry-run` prints the prompts without calling Gemini.

### Examples
Each folder in [`examples/general/`](examples/general/) and [`examples/prairielearn/`](examples/prairielearn/) is a case.

To update every example's `out/` after a code change, run [`evaluation/update_outputs.py`](evaluation/update_outputs.py):
```bash
python -m evaluation.update_outputs [--detection-model MODEL] [--detection-variant all|images|boxes|no_snapshots] [--detection-dry-run]
```

It always runs both modes, and runs every variant unless `--detection-variant` picks one. The other flags work as in `pipeline.py`.

The pages in `examples/general/` are re-rendered from [WUICC](https://huggingface.co/datasets/zhangsan11111122/WUICC), which is built on [WebSight](https://huggingface.co/datasets/HuggingFaceM4/WebSight), and the synthetic ones use text from WUICC pages. WUICC and WebSight are both [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).


Note: for synthetic_five_changes, the case introduces intentional regression. The deliberate design_intent.md is: 

the "Savings Accounts" card was not changed at all. 

But in the actual code, the Savings Accounts is changed from green to red. 


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

Generated specs use the PrairieLearn fork's shared E2E snapshot helper so screenshots
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

The script is [`regression_detection/gemini_processor.py`](regression_detection/gemini_processor.py).

It takes the image diff output folder of a case, like [`examples/general/button_enlarged/out/dom`](examples/general/button_enlarged/out/dom).

That folder contains `before_color.png`, `after_color.png`, `before_shape.png`, `after_shape.png` and `boxes.json`. [`pipeline.py`](pipeline.py) also passes `design_intent.md` and `design_language.md` from the case's `design/` folder if it exists.

### Run and Operation 

To do a dry run (without calling Gemini, checking inputs): 
```
python regression_detection/gemini_processor.py run "folder-containing-images" --mode both --dry-run
```
To do a complete run (calling Gemini): 
```
python regression_detection/gemini_processor.py run "folder-containing-images" --mode both
```

### Parameters
`--mode` takes three values: `both`, `baseline`, `context`

Both runs both baseline and context

Baseline takes in only the 4 images + boxes.json without any design context. 

Context takes in the 4 images + boxes.json + design intent and design language.

`--variant` takes the same values as `--detection-variant` above, `all` by default. For `no_snapshots`, we pass the case's `out/pixel` folder instead of `out/dom`.

### Output
Each report ends with a `usage` block with the text, image, output, thinking and total token counts from the API response.

### Generate a DOM snapshot test

Generate a `unittest` that checks a captured DOM snapshot against either the
before or after page state:
```bash
python -m image_diff.generate_snapshot_test \
  captures/before_snapshot.json captures/after_snapshot.json \
  --side after --output tests/generated/test_capture.py
```

The command writes `test_capture.expected.json` beside the test. Capture the
page under test using the same snapshot format, then run the test from the
repository root:
```bash
ACTUAL_SNAPSHOT=/path/to/current_snapshot.json \
  python -m unittest discover -s tests/generated -p 'test_capture.py'
```
Use `--side before` to make the test expect the before state instead. It
compares parsed rendered elements, layout, text, attributes, and computed
styles; volatile raw CDP node identifiers are not compared. `--force` replaces
generated files with the same names.


## Evaluation

[`evaluation/score.py`](evaluation/score.py) compares the saved reports with hand-written labels and does not call Gemini:
```bash
python -m evaluation.score
```

The label for `examples/<group>/<case>/` goes in `evaluation/labels/<group>/<case>.json`:
```json
{"regression": true, "dom_boxes": [3], "pixel_boxes": [4]}
```

`regression` says whether the case is a regression. `dom_boxes` is optional and lists the ids of the regressed boxes in `out/dom/boxes.json`. `pixel_boxes` is also optional and lists the regressed boxes by their ids in `out/pixel/boxes.json`, since a box has a different id there than in `out/dom/boxes.json`. The `no_snapshots` variant is scored based on it. The script prints case and box precision and recall for each model, variant and mode.


## LLM based test generation 

### Installation

To run this, you will need to install claude code. 
[Installation Instructions](https://code.claude.com/docs/en/quickstart)

To date I have not yet figured out how to share my claude subscription. 

----

### Run

['test_generation/llm_test_generation.py'](test_generation/llm_test_generation.py) generates a test written by Claude Code if regression is found from a existing report, otherwise, no tests are generated. 

To run on a specific folder (test): 
```bash
python -m test_generation.llm_test_generation examples/general/synthetic_five_changes
```

To do a dry run: 

```bash
python -m test_generation.llm_test_generation examples/general/synthetic_five_changes --dry-run
```

To run an example entire folder 

```bash
for d in examples/general/*/; do python -m test_generation.llm_test_generation "$d" --run-detection; done
```

Note: if an regression is introduced, the pipeline must be ran to update the results that this script relies on. Else, old results will be fed into the script. 

---

### Results

For a json result, look under the test, for example, for the test ```synthetic_five_changes```, results can be found in the folder: 

```
examples/general/synthetic_five_changes/out/test_generation/gemini-3.5-flash-lite/all/sonnet/
```

What is inside: 
- <code>result.json</code>: the status (generated, skipped, invalid or agent_error), whether the test passed on the before snapshot and failed on the after snapshot, and token usage and cost.
- <code>test_generated_regression.py</code>: the generated test. It should pass on the before snapshot and fail on an assertion on the after snapshot.

Note: if no regression is found, you should not be seeing a <code>test_generated_regression.py</code> file. 