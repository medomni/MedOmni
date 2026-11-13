"""Container API server, the same in every encoder image.

    python -m medomni.perception.runtime.serve serve                       # HTTP, the real contract
    python -m medomni.perception.runtime.serve encode --family F --path P  # one call, JSON on stdout

The second form exists so a check needs no port and no network. Both forms go through run_encode, so they cannot
diverge.
"""
import argparse
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .adapter import check_adapter, load_adapter, load_card
from .decoders import read_family
from .errors import BadRequest, Degraded
from .request import parse_request, resolve_path
from .response import response

MAX_BODY = 1 << 20


def run_encode(card, adapter, body, data_root=None, model=None):
    """The whole call path: validate, decode, encode, wrap. Raises BadRequest."""
    check_adapter(card, adapter)
    family, rel, options = parse_request(body, card)
    path = resolve_path(rel, data_root)
    started = time.time()
    notes = []
    # Decoding degrades too: a file that does not conform to the family is
    # unusable input, and unusable input is data. Only a crash is an error.
    try:
        sample = read_family(family, path, data_root)
        # One list, shared with the adapter. The decoder says what it could not
        # read; an adapter appends what it had to do to the sample it was given.
        # Both are the caller's business, so both reach notes.
        notes = sample["notes"] = list(sample.get("notes") or [])
        if model is not None:
            options = dict(options, _model=model)
        outputs = adapter.encode(sample, options)
    except Degraded as exc:
        return response(card, [], notes + [str(exc)], healthy=False,
                                 duration_ms=round((time.time() - started) * 1000, 1))
    return response(card, outputs, notes,
                             duration_ms=round((time.time() - started) * 1000, 1))


def content_length(value):
    """Parse and limit Content-Length. Raise BadRequest for invalid input."""
    try:
        length = int(value or 0)
    except (TypeError, ValueError):
        raise BadRequest("content-length must be a non-negative integer") from None
    if length < 0:
        raise BadRequest("content-length must be a non-negative integer")
    if length > MAX_BODY:
        raise BadRequest("body too large")
    return length


class Handler(BaseHTTPRequestHandler):
    card = None
    adapter = None
    model = None

    def _send(self, status, payload):
        blob = json.dumps(payload, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(blob)))
        self.end_headers()
        self.wfile.write(blob)

    def do_GET(self):
        if self.path == "/healthz":
            self._send(200, {"ok": True, "encoder_id": self.card["id"], "ready": True})
        elif self.path == "/card":
            self._send(200, self.card)
        else:
            self._send(404, {"error": f"no such endpoint: {self.path}"})

    def do_POST(self):
        if self.path != "/encode":
            self._send(404, {"error": f"no such endpoint: {self.path}"})
            return
        try:
            length = content_length(self.headers.get("content-length"))
        except BadRequest as exc:
            self._send(400, {"error": str(exc)})
            return
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except ValueError as exc:
            self._send(400, {"error": f"body is not JSON: {exc}"})
            return
        try:
            self._send(200, run_encode(self.card, self.adapter, body, model=self.model))
        except BadRequest as exc:
            self._send(400, {"error": str(exc)})
        except Exception as exc:                      # the model itself failed
            self._send(500, {"error": f"{type(exc).__name__}: {exc}"})

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd")
    srv = sub.add_parser("serve")
    srv.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8080)))
    enc = sub.add_parser("encode")
    enc.add_argument("--family", required=True)
    enc.add_argument("--path", required=True)
    enc.add_argument("--data-root")
    enc.add_argument("--options-json", default="{}")
    args = parser.parse_args(argv)

    card, adapter = load_card(), load_adapter()
    check_adapter(card, adapter)
    model = adapter.load() if hasattr(adapter, "load") else None

    if args.cmd == "encode":
        try:
            options = json.loads(args.options_json)
        except ValueError as exc:
            parser.error(f"--options-json is not JSON: {exc}")
        if not isinstance(options, dict):
            parser.error("--options-json must contain an object")
        body = {"family": args.family, "path": args.path, "options": options}
        try:
            out = run_encode(card, adapter, body, data_root=args.data_root, model=model)
        except BadRequest as exc:
            print(json.dumps({"error": str(exc)}))
            return 1
        print(json.dumps(out, indent=1))
        return 0

    Handler.card, Handler.adapter, Handler.model = card, adapter, model
    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    sys.stderr.write(f"{card['id']} ready on :{args.port}\n")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
