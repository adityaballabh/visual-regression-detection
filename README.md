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

## Attribution
The example pages in `image_diff/examples/` are re-rendered from [WUICC](https://huggingface.co/datasets/zhangsan11111122/WUICC), which is built on [WebSight](https://huggingface.co/datasets/HuggingFaceM4/WebSight). Both are [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/).


## LLM 

The script lives in the <code>/llm</code> folder, called <code>gemini_processor.py</code>. 

The script ideally takes input from any folder. However, for structure, put all inputs in the <code>/input</code> folder. 

Input structure: 
```/llm/<your change test set>/dom```

Inside dom: 
```
	After_color.png 
	After_shape.png
	Before_color.png
	Before_shape.png
	Boxes.json
```

### Environment setup 

Create an .env file in the root project folder (visual-regression-detection), not in llm. 

Put 
```GEMINI_API_KEY=redacted ```

(find API key in proposal doc)

as content for .env

Create a python env and install the gemini packages: 
```
python3 -m venv .venv && source .venv/bin/activate && pip install google-genai pydantic
```

### Run and Operation 

To do a dry run (without calling gemini, checking inputs): 
```
python llm/gemini_processor.py run "folder-containing-images" --mode both --dry-run
```
To do a complete run (calling gemini): 
```
python llm/gemini_processor.py run "folder-containing-images" --mode both
```

### Parameters
–mode takes three parameters: ```both, baseline, context ```

Both runs both baseline and context

Baseline takes in only the 4 images + boxes.json without any design context. 

Context takes in the 4 images + boxes.json + PR link, design context and intent. 
