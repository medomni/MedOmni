"""Studio report tool: draw the architecture diagrams from one description.

Reads a YAML file of diagrams (frames, boxes, arrows, positions) and writes one `<name>.drawio.svg` per diagram:
plain SVG to display, with the same drawing embedded as a draw.io model, so the file also opens and edits in draw.io.

    uv run python src/medomni/studio/report/diagrams.py docs/assets/diagrams.yaml docs/assets/

Style: one colour per part, boxes tagged [Person] / [Container: tech] / [External System], straight dashed arrows
labelled "what [tech]", a key row at the bottom. Standard library and PyYAML only.
"""
import html
import sys
from pathlib import Path

import yaml

FONT = "Helvetica, Arial, sans-serif"
INK, GREY, TINT, WHITE = "#212121", "#424242", "#E0E0E0", "#FFFFFF"


def esc(s):
    return html.escape(str(s), quote=True)


def text(x, y, s, size, color, weight="normal", italic=False, anchor="middle"):
    st = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="{FONT}" font-size="{size}" '
            f'font-weight="{weight}"{st} fill="{color}">{esc(s)}</text>')


def width_of(s, size):
    return len(str(s)) * size * 0.5


class Diagram:
    def __init__(self, spec, parts):
        self.d, self.parts = spec, parts
        self.boxes = {b["id"]: b for b in spec.get("boxes", [])}

    def colour(self, part):
        return self.parts[part]["colour"] if part in self.parts else GREY

    def box_style(self, b):
        kind, c = b.get("kind", "internal"), self.colour(b.get("part"))
        if kind == "external":
            return WHITE, c, INK, GREY
        if kind == "data":
            return TINT, INK, INK, GREY
        return c, c, WHITE, WHITE  # internal, person, system: filled

    # ------------------------------------------------------------ svg
    def svg(self):
        W, H = self.d["width"], self.d["height"]
        out = [f'<rect width="{W}" height="{H}" fill="{WHITE}"/>']
        for f in self.d.get("frames", []):
            c = self.colour(f.get("part"))
            out.append(f'<rect x="{f["x"]}" y="{f["y"]}" width="{f["w"]}" height="{f["h"]}" rx="6" fill="none" '
                       f'stroke="{c}" stroke-width="1.6" stroke-dasharray="7 4"/>')
            out.append(text(f["x"] + 12, f["y"] + 20, f["label"], 13, c, "bold", anchor="start"))
        for b in self.d.get("boxes", []):
            fill, stroke, t1, t2 = self.box_style(b)
            out.append(f'<rect x="{b["x"]}" y="{b["y"]}" width="{b["w"]}" height="{b["h"]}" rx="6" fill="{fill}" '
                       f'stroke="{stroke}" stroke-width="1.6"/>')
            lines = [(b["title"], 14, t1, "bold", False)]
            if b.get("tag"):
                lines.append((f'[{b["tag"]}]', 11, t2, "normal", True))
            lines += [(s, 11.5, t2, "normal", False) for s in b.get("desc", [])]
            heights = [17 if i == 0 else 15 for i in range(len(lines))]
            y = b["y"] + b["h"] / 2 - sum(heights) / 2 + 12
            for (s, size, col, wt, it), h in zip(lines, heights):
                out.append(text(b["x"] + b["w"] / 2, y, s, size, col, wt, it))
                y += h
        for e in self.d.get("edges", []):
            (x1, y1), (x2, y2) = self.ends(e)
            red = e.get("highlight")
            out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{GREY}" '
                       f'stroke-width="1.4" stroke-dasharray="6 4" marker-end="url(#{"red" if red else "arrow"})"/>')
            lx, ly = e.get("label_at", ((x1 + x2) / 2 + 6, (y1 + y2) / 2 - 8))
            parts = [e["label"], f'[{e["tech"]}]' if e.get("tech") else None]
            if e.get("one_line"):  # for narrow gaps: "label [tech]" on one line
                parts = [" ".join(x for x in parts if x), None]
            for i, s in enumerate(parts):
                if not s:
                    continue
                w = width_of(s, 11)
                out.append(f'<rect x="{lx - 2:.1f}" y="{ly + 13 * i - 11:.1f}" width="{w + 4:.1f}" height="15" '
                           f'fill="{WHITE}"/>')
                out.append(text(lx, ly + 13 * i, s, 11, INK if i == 0 else GREY, italic=i == 1, anchor="start"))
        out += self.key(H)
        defs = ('<defs>' + ''.join(
            f'<marker id="{n}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
            for n, c in (("arrow", GREY), ("red", "#C00000"))) + '</defs>')
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
                f'content="{esc(self.mxfile())}">{defs}{"".join(out)}</svg>\n')

    def key(self, H):
        y, x, out = H - 37, 20.0, [text(20, H - 45, "Key", 12, INK, "bold", anchor="start")]
        items = []
        for label, part in self.d.get("key", []):  # [label, part | "data" | "external"]
            if part == "data":
                items.append((label, TINT, INK))
            elif part == "external":
                items.append((label, WHITE, GREY))
            else:
                items.append((label, self.colour(part), self.colour(part)))
        for label, fill, stroke in items:
            out.append(f'<rect x="{x:.1f}" y="{y}" width="22" height="16" rx="3" fill="{fill}" stroke="{stroke}" '
                       f'stroke-width="1.4"/>')
            out.append(text(x + 28, y + 12, label, 11.5, INK, anchor="start"))
            x += 28 + width_of(label, 11.5) + 26
        out.append(f'<line x1="{x:.1f}" y1="{y + 8}" x2="{x + 34:.1f}" y2="{y + 8}" stroke="{GREY}" stroke-width="1.4" '
                   f'stroke-dasharray="6 4" marker-end="url(#arrow)"/>')
        out.append(text(x + 40, y + 12, "Uses [tech]", 11.5, INK, anchor="start"))
        return out

    def ends(self, e):
        a, b = self.boxes[e["from"]], self.boxes[e["to"]]
        return self.anchor(a, e.get("from_side"), b), self.anchor(b, e.get("to_side"), a)

    @staticmethod
    def anchor(b, side, other):
        cx, cy = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
        if side is None:
            ox, oy = other["x"] + other["w"] / 2, other["y"] + other["h"] / 2
            dx, dy = ox - cx, oy - cy
            side = ("right" if dx > 0 else "left") if abs(dx) * b["h"] > abs(dy) * b["w"] else ("bottom" if dy > 0 else "top")
        if isinstance(side, list):  # [side, fraction along that side]
            s, f = side
            return {"top": (b["x"] + b["w"] * f, b["y"]), "bottom": (b["x"] + b["w"] * f, b["y"] + b["h"]),
                    "left": (b["x"], b["y"] + b["h"] * f), "right": (b["x"] + b["w"], b["y"] + b["h"] * f)}[s]
        return {"top": (cx, b["y"]), "bottom": (cx, b["y"] + b["h"]), "left": (b["x"], cy),
                "right": (b["x"] + b["w"], cy)}[side]

    # ------------------------------------------------------------ draw.io model
    def mxfile(self):
        cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']

        def vertex(i, value, style, x, y, w, h):
            cells.append(f'<mxCell id="{esc(i)}" value="{esc(value)}" style="{style}" vertex="1" parent="1">'
                         f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')

        for n, f in enumerate(self.d.get("frames", [])):
            c = self.colour(f.get("part"))
            vertex(f"frame{n}", f"<b>{esc(f['label'])}</b>",
                   f"rounded=1;arcSize=2;whiteSpace=wrap;html=1;fillColor=none;strokeColor={c};strokeWidth=1.6;"
                   f"dashed=1;dashPattern=7 4;verticalAlign=top;align=left;spacingLeft=10;fontColor={c};fontSize=13;"
                   f"fontFamily={FONT}", f["x"], f["y"], f["w"], f["h"])
        for b in self.d.get("boxes", []):
            fill, stroke, t1, _ = self.box_style(b)
            v = f"<b style='font-size:14px'>{esc(b['title'])}</b>"
            if b.get("tag"):
                v += f"<br><i style='font-size:11px'>[{esc(b['tag'])}]</i>"
            v += "".join(f"<br>{esc(s)}" for s in b.get("desc", []))
            vertex(b["id"], v, f"rounded=1;arcSize=6;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
                               f"strokeWidth=1.6;fontColor={t1};fontSize=11.5;fontFamily={FONT}",
                   b["x"], b["y"], b["w"], b["h"])
        for n, e in enumerate(self.d.get("edges", [])):
            v = esc(e["label"]) + (f"<br><i>[{esc(e['tech'])}]</i>" if e.get("tech") else "")
            cells.append(f'<mxCell id="edge{n}" value="{esc(v)}" style="html=1;rounded=0;strokeColor={GREY};'
                         f'strokeWidth=1.4;dashed=1;dashPattern=6 4;endArrow=block;endFill=1;fontSize=11;'
                         f'fontFamily={FONT};labelBackgroundColor={WHITE}" edge="1" parent="1" '
                         f'source="{esc(e["from"])}" target="{esc(e["to"])}"><mxGeometry relative="1" as="geometry"/>'
                         f'</mxCell>')
        name = self.d["title"]
        return (f'<mxfile host="drawio"><diagram name="{esc(name)}" id="{esc(name)}"><mxGraphModel grid="1" '
                f'gridSize="10" page="0" pageWidth="{self.d["width"]}" pageHeight="{self.d["height"]}" '
                f'background="{WHITE}"><root>{"".join(cells)}</root></mxGraphModel></diagram></mxfile>')


def main(spec_path, out_dir):
    spec = yaml.safe_load(Path(spec_path).read_text())
    out = Path(out_dir)
    for name, d in spec["diagrams"].items():
        (out / f"{name}.drawio.svg").write_text(Diagram(d, spec["parts"]).svg())
        print(f"wrote {name}.drawio.svg: {len(d.get('boxes', []))} boxes, {len(d.get('edges', []))} arrows")


if __name__ == "__main__":
    main(*sys.argv[1:3])
