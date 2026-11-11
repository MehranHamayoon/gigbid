"""Render the source article as a small static personal blog post."""
import re
from html import escape

from agent.settings import ROOT


def body(text):
    output = []
    for paragraph in text.strip().split("\n\n"):
        paragraph = paragraph.strip()
        if paragraph.startswith("# "):
            output.append(f"<h1>{escape(paragraph[2:])}</h1>")
        elif paragraph.startswith("## "):
            output.append(f"<h2>{escape(paragraph[3:])}</h2>")
        else:
            rendered = re.sub(r"\[([^\]]+)\]\((https://[^)]+)\)", r'<a href="\2">\1</a>', escape(paragraph))
            output.append(f"<p>{rendered}</p>")
    return "\n".join(output)


if __name__ == "__main__":
    text = (ROOT / "docs/TECHNICAL_WRITEUP.md").read_text(encoding="utf-8")
    document = """<!doctype html><html lang="en"><head><meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>A perfect evidence match still earned zero replies · GigBid</title>
    <style>body{margin:0;background:#f6f8f1;color:#16382b;font:18px/1.62 Georgia,serif}
    article{max-width:720px;margin:auto;padding:42px 20px 72px} h1,h2,nav{font-family:system-ui,sans-serif}
    h1{font-size:clamp(2.35rem,6vw,3.7rem);line-height:1.06;letter-spacing:-.045em;margin:24px 0}
    h2{font-size:1.42rem;margin:32px 0 10px} nav{font-size:.85rem;font-weight:700;border-bottom:1px solid #c6dacb;padding-bottom:14px}
    a{color:#17634a} h1+p{color:#526a5d;font:14px system-ui,sans-serif;margin-bottom:32px}</style>
    </head><body><article><nav><a href="/">GigBid</a> / Field notes</nav>"""
    (ROOT / "docs/public/field-notes.html").write_text(document + body(text) + "</article></body></html>\n", encoding="utf-8")
