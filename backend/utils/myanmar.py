"""Burmese (Myanmar script) text for ReportLab PDFs.

Two separate problems have to be solved before Burmese can appear on a slip:

1. GLYPHS. The built-in PDF fonts (Helvetica & co.) are Latin-1 only, so every
   Burmese character came out as a hollow box. Fixed by embedding Noto Sans
   Myanmar (SIL Open Font License) from ../assets/fonts.

2. SHAPING. Burmese is a complex script: it is *stored* in one order and
   *drawn* in another. "ကေ" is stored as က + ေ but must be drawn ေ first;
   medial ra wraps around its consonant; U+1039 stacks the next consonant
   underneath. ReportLab draws characters straight through in stored order, so
   simply embedding a font is not enough — the result is readable-ish nonsense.
   HarfBuzz (uharfbuzz) does the reordering and ligature work for us.

HarfBuzz returns GLYPH IDs, but ReportLab can only draw CHARACTERS. The bridge
is a derived copy of the font whose cmap maps a private-use codepoint to every
glyph (U+E000 + glyph_id). We shape the text, translate the resulting glyph ids
into that private-use range, and hand ReportLab an ordinary string — so
Paragraph, Table and the rest of the layout engine keep working untouched.

If the font or uharfbuzz is missing, every function degrades to returning the
text unchanged: PDFs still build (with boxes for Burmese) instead of erroring.
"""
import io
import os
import re
from functools import lru_cache
from xml.sax.saxutils import escape

# Myanmar block + the Extended-A/B blocks used by minority-language text.
MYANMAR_RE = re.compile(r"[က-႟ꧠ-꧿ꩠ-ꩿ]")

_FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "assets", "fonts")
FONT_FILE = os.path.join(_FONT_DIR, "NotoSansMyanmar-Regular.ttf")

# Name the shaped font is registered under with ReportLab.
FONT_NAME = "NotoSansMyanmar"
# Glyph ids are exposed as characters starting here. The font has ~600 glyphs;
# the private use area (U+E000..U+F8FF) holds 6400, so there is ample room.
_PUA_BASE = 0xE000
_PUA_LIMIT = 0xF8FF


def has_myanmar(text) -> bool:
    """True when the value contains any Burmese character."""
    return bool(MYANMAR_RE.search(str(text))) if text is not None else False


@lru_cache(maxsize=1)
def _hb_font():
    """A HarfBuzz font for shaping, or None when unavailable."""
    try:
        import uharfbuzz as hb
    except ImportError:
        return None
    if not os.path.exists(FONT_FILE):
        return None
    with open(FONT_FILE, "rb") as fh:
        blob = hb.Blob(fh.read())
    return hb.Font(hb.Face(blob))


@lru_cache(maxsize=1)
def _shaped_font_bytes():
    """The font re-cmapped so every glyph is reachable as U+E000 + glyph_id."""
    from fontTools.ttLib import TTFont
    from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

    font = TTFont(FONT_FILE)
    order = font.getGlyphOrder()
    if _PUA_BASE + len(order) > _PUA_LIMIT:
        raise ValueError(f"{len(order)} glyphs will not fit in the private use area")

    sub = CmapSubtable.newSubtable(4)
    sub.platformID, sub.platEncID, sub.language = 3, 1, 0
    sub.cmap = {_PUA_BASE + gid: name for gid, name in enumerate(order)}
    font["cmap"].tables = [sub]

    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


@lru_cache(maxsize=1)
def register_font():
    """Register the shaped font with ReportLab. Returns True when Burmese is
    renderable; False (once, quietly) when the font or shaper is missing."""
    if _hb_font() is None:
        return False
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont as RLFont

        pdfmetrics.registerFont(RLFont(FONT_NAME, io.BytesIO(_shaped_font_bytes())))
        return True
    except Exception:            # noqa: BLE001 — a PDF without Burmese beats no PDF
        return False


def shape(text: str) -> str:
    """Burmese text -> a string of private-use characters in DRAWN order.

    Only meaningful together with FONT_NAME; returns the input unchanged when
    shaping is unavailable.
    """
    font = _hb_font()
    if font is None or not text:
        return text
    import uharfbuzz as hb

    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()          # script=Mymr, direction=ltr
    hb.shape(font, buf)
    return "".join(chr(_PUA_BASE + g.codepoint) for g in buf.glyph_infos)


def _convert(text, esc) -> str:
    s = "" if text is None else str(text)
    keep = escape if esc else (lambda x: x)
    if not has_myanmar(s) or not register_font():
        return keep(s)

    out, last = [], 0
    # a run is a stretch of Burmese plus any spaces/marks that sit inside it
    for m in re.finditer(r"[က-႟ꧠ-꧿ꩠ-ꩿ​‌‍ ]+", s):
        run = m.group()
        if not has_myanmar(run):
            continue
        out.append(keep(s[last:m.start()]))
        lead = run[:len(run) - len(run.lstrip(" "))]
        trail = run[len(run.rstrip(" ")):]
        out.append(lead)
        out.append(f'<font name="{FONT_NAME}">{escape(shape(run.strip(" ")))}</font>')
        out.append(trail)
        last = m.end()
    out.append(keep(s[last:]))
    return "".join(out)


def markup(text) -> str:
    """Paragraph markup for a PLAIN value (a name, an address, a table cell).

    The whole string is XML-escaped, then every Burmese run is shaped and
    switched to the embedded font. Latin/digits keep the surrounding font.
    """
    return _convert(text, esc=True)


def inline(text) -> str:
    """Same, for a string that ALREADY contains Paragraph markup (`<b>`,
    `&nbsp;` …). Existing tags are left alone, so only the Burmese is touched.
    """
    return _convert(text, esc=False)


def cell(value, style):
    """A table cell that renders Burmese correctly.

    Plain values are returned untouched so existing tables keep their exact
    look; only cells containing Burmese are promoted to a Paragraph (the only
    flowable that can switch fonts mid-string).
    """
    if value is None:
        return ""
    if not has_myanmar(value):
        return value
    from reportlab.platypus import Paragraph
    return Paragraph(markup(value), style)
