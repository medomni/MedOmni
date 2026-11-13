## Tools

{toolset}

### Perception encoders (optional, recommended)

A perception service at `http://perception:8899` runs pretrained medical encoders over the staged signal and image files. It is optional: every file can be read directly. It is recommended because for some families — images especially — an encoder may be the only way to get a clinical reading at all. It is not perfectly reliable: a call may come back `healthy: false`, time out, or not apply to a file. Weigh what it returns against what you can check yourself.

`/workspace/data/encoder_manifest.md` lists the encoders available for this task.

- `GET /encoders` lists them; `GET /cards/{id}` gives one encoder's details, limits and options.
- `POST /encode` with `{"encoder_id": "...", "path": "<path relative to /workspace/data>", "options": {}}` runs one encoder on one file.
- 502 or 503: a cold or crashed encoder — retry once or twice. 400 or 422: the request was wrong. 429: this task's call budget is used up.
