"""Core engine for the blog image generator.

Pipeline:
  1. Style-locked prompt  ->  free AI image (Pollinations, no key / Gemini free tier)
  2. Title is composited LOCALLY with Pillow (so text is always crisp & readable)

Nothing here costs money. Pollinations needs no API key at all.
"""
import io
import os
import re
import time
from urllib.parse import quote

import requests
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(BASE, "assets", "fonts")
OUT_DIR = os.path.join(BASE, "output")

# ---------------------------------------------------------------- themes ---
# 15 colour themes. `panel` = dark side/bottom panel, `accent` = highlight bar,
# `palette` = words injected into the image prompt so the illustration matches.
THEMES = [
    {"id": "navy",     "name": "Navy Blue",     "panel": (23, 37, 66),   "accent": (56, 189, 248),  "palette": "deep navy blue and sky cyan", "avoid": "yellow, orange, red, dark or black background"},
    {"id": "emerald",  "name": "Emerald Green", "panel": (6, 60, 45),    "accent": (52, 211, 153),  "palette": "emerald green and mint", "avoid": "red, purple, orange, dark or black background"},
    {"id": "violet",   "name": "Violet",        "panel": (46, 24, 90),   "accent": (167, 139, 250), "palette": "violet purple and lavender", "avoid": "green, yellow, orange, dark or black background"},
    {"id": "crimson",  "name": "Crimson Red",   "panel": (90, 18, 26),   "accent": (248, 113, 113), "palette": "crimson red and soft rose", "avoid": "green, blue, purple, dark or black background"},
    {"id": "amber",    "name": "Amber Gold",    "panel": (80, 45, 8),    "accent": (251, 191, 36),  "palette": "amber orange and warm gold", "avoid": "blue, purple, green, dark or black background"},
    {"id": "teal",     "name": "Teal",          "panel": (12, 62, 66),   "accent": (45, 212, 191),  "palette": "teal and turquoise", "avoid": "red, orange, purple, dark or black background"},
    {"id": "indigo",   "name": "Indigo",        "panel": (30, 35, 90),   "accent": (129, 140, 248), "palette": "indigo blue and periwinkle", "avoid": "green, yellow, orange, dark or black background"},
    {"id": "rose",     "name": "Rose Pink",     "panel": (88, 22, 52),   "accent": (251, 113, 133), "palette": "rose pink and magenta", "avoid": "green, blue, dark or black background"},
    {"id": "slate",    "name": "Slate Gray",    "panel": (30, 41, 59),   "accent": (148, 163, 184), "palette": "slate gray and silver blue", "avoid": "bright saturated colors, dark or black background"},
    {"id": "forest",   "name": "Forest Green",  "panel": (20, 60, 35),   "accent": (134, 239, 172), "palette": "forest green and lime", "avoid": "red, purple, pink, dark or black background"},
    {"id": "midnight", "name": "Midnight",      "panel": (15, 18, 45),   "accent": (96, 165, 250),  "palette": "midnight blue and electric blue", "avoid": "yellow, orange, green, gray background"},
    {"id": "copper",   "name": "Copper",        "panel": (70, 35, 15),   "accent": (251, 146, 60),  "palette": "burnt orange and copper", "avoid": "blue, green, purple, dark or black background"},
    {"id": "burgundy", "name": "Burgundy",      "panel": (75, 20, 35),   "accent": (244, 114, 182), "palette": "burgundy wine and blush pink", "avoid": "green, blue, yellow, dark or black background"},
    {"id": "charcoal", "name": "Charcoal Gold", "panel": (28, 28, 32),   "accent": (250, 204, 21),  "palette": "charcoal black and gold", "avoid": "neon green, neon pink, dark gray background"},
    {"id": "steel",    "name": "Steel Blue",    "panel": (35, 60, 85),   "accent": (125, 211, 252), "palette": "steel blue and ice blue", "avoid": "red, orange, yellow, dark or black background"},
]
THEME_MAP = {t["id"]: t for t in THEMES}

# ------------------------------------------------------- style-lock prompt ---
# This fixed template is what keeps every image in the SAME design language,
# exactly like your reference: 3D isometric stack + floating icon cards.
STYLE_LOCK = (
    "Isometric 3D illustration, corporate infographic style, bright white background. "
    "A technology platform visualized as a layered cake: 4 to 5 wide flat rectangular slabs "
    "stacked vertically, alternating {palette} and white, centered on a subtle round platform. "
    "A few small white square icon tiles float around the stack, each carrying a simple "
    "{palette} pictogram of a database, a cloud, a gear or a server. "
    "Clean, sharp, detailed professional 3D render, soft daylight, subtle shadows. "
    "Strict color scheme: {palette} with white and light gray only — no other colors. "
    "Visual topic: {topic}. "
    "Absolutely no text, no letters, no words, no numbers, no watermark, no logo. "
    "Avoid: {avoid}."
)

STOPWORDS = set(
    "a an the and or of on in to for with by from as at is are was were be been "
    "this that these those it its into over under between vs via inside new perspective "
    "perspectives guide ultimate complete how what why when where your you we our top best".split()
)


def extract_keywords(title, max_words=8):
    """Turn a blog title into short visual keywords for the image prompt."""
    words = re.findall(r"[A-Za-z0-9]+", title)
    kept = []
    for w in words:
        lw = w.lower()
        if lw in STOPWORDS or len(w) < 3:
            continue
        if lw not in [k.lower() for k in kept]:
            kept.append(w)
        if len(kept) >= max_words:
            break
    return " ".join(kept) if kept else "technology concept"


def build_prompt(title, theme, visual_hint=None):
    topic = visual_hint.strip() if visual_hint and visual_hint.strip() else extract_keywords(title)
    return STYLE_LOCK.format(topic=topic, palette=theme["palette"],
                             avoid=theme.get("avoid", "dark background"))


# ------------------------------------------------------------------ fonts ---
FONT_URLS = {
    "Poppins-Bold.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-Bold.ttf",
    "Poppins-Regular.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-Regular.ttf",
}


def ensure_fonts():
    """Download free Poppins fonts once (Google Fonts, OFL licence)."""
    os.makedirs(FONTS_DIR, exist_ok=True)
    paths = {}
    for fname, url in FONT_URLS.items():
        dest = os.path.join(FONTS_DIR, fname)
        if not os.path.exists(dest):
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            with open(dest, "wb") as f:
                f.write(r.content)
        kind = "bold" if "Bold" in fname else "regular"
        paths[kind] = dest
    return paths


# --------------------------------------------------------------- providers ---
def fetch_pollinations(prompt, seed, size=1024, model="flux", timeout=240):
    """Free text-to-image, no API key. https://pollinations.ai"""
    url = "https://image.pollinations.ai/prompt/" + quote(prompt, safe="")
    params = {
        "width": size, "height": size, "seed": seed, "model": model,
        "nologo": "true", "private": "true", "enhance": "false",
    }
    last_err = "unknown"
    for _ in range(3):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            ctype = r.headers.get("Content-Type", "")
            if r.status_code == 200 and ctype.startswith("image"):
                return Image.open(io.BytesIO(r.content)).convert("RGB")
            last_err = f"HTTP {r.status_code} ({ctype})"
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
        time.sleep(3)
    raise RuntimeError(f"Pollinations failed after retries: {last_err}")


# Gemini image models, tried in order (Google retires old ones regularly).
# gemini-2.5-flash-image = free-tier native image generation (stable).
# gemini-3.1-flash-image  = "Nano Banana 2", current mainstream GA model.
GEMINI_IMAGE_MODELS = ["gemini-2.5-flash-image", "gemini-3.1-flash-image"]


def fetch_gemini(prompt, seed, api_key):
    """Gemini free tier (AI Studio key). Needs: pip install google-genai"""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise RuntimeError("google-genai not installed. Run: pip install google-genai")
    client = genai.Client(api_key=api_key)
    last_err = "unknown"
    for model in GEMINI_IMAGE_MODELS:
        try:
            resp = client.models.generate_content(
                model=model,
                contents=f"{prompt} (variation seed {seed})",
                config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
            )
            for part in resp.candidates[0].content.parts:
                inline = getattr(part, "inline_data", None)
                if inline and inline.data:
                    return Image.open(io.BytesIO(inline.data)).convert("RGB")
            last_err = f"{model}: no image in response"
        except Exception as e:  # noqa: BLE001
            last_err = f"{model}: {e}"
    raise RuntimeError(f"Gemini failed: {last_err}")


def generate_illustration(prompt, seed, provider="pollinations", size=1024, model="flux", api_key=None):
    if provider == "gemini":
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY not set (env var or --gemini-key).")
        return fetch_gemini(prompt, seed, key)
    return fetch_pollinations(prompt, seed, size=size, model=model)


# -------------------------------------------------------------- compositing ---
def crop_fill(img, w, h):
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    img = img.resize((int(iw * scale + 0.5), int(ih * scale + 0.5)), Image.LANCZOS)
    x = (img.width - w) // 2
    y = (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def draw_wrapped_title(draw, text, box, font_path, max_size, min_size, fill):
    """Greedy word-wrap + auto-shrink so the title always fits the panel."""
    x0, y0, x1, y1 = box
    max_w, max_h = x1 - x0, y1 - y0
    size = max_size
    lines, font, lh = [text], None, 0
    while size >= min_size:
        font = ImageFont.truetype(font_path, size)
        lines, cur = [], ""
        for wd in text.split():
            trial = (cur + " " + wd).strip()
            if draw.textlength(trial, font=font) <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = wd
        if cur:
            lines.append(cur)
        # hard-break a single overlong word
        fixed = []
        for ln in lines:
            while draw.textlength(ln, font=font) > max_w and len(ln) > 1:
                fixed.append(ln[: max(1, int(len(ln) * max_w / draw.textlength(ln, font=font)))])
                ln = ln[len(fixed[-1]):]
            fixed.append(ln)
        lines = fixed
        lh = int(size * 1.12)
        if lh * len(lines) <= max_h:
            break
        size -= 2
    font = ImageFont.truetype(font_path, max(size, min_size))
    lh = int(max(size, min_size) * 1.12)
    y = y0 + max(0, (max_h - lh * len(lines)) // 2)
    for ln in lines:
        draw.text((x0, y), ln, font=font, fill=fill)
        y += lh


# Output sizes: desktop + mobile, both half-half (illustration | text panel).
SIZES = {
    "desktop": (1200, 629),
    "mobile": (450, 236),
}


def compose(title, illustration, theme, layout="right", subtitle="", size="desktop"):
    """Blog graphic: AI illustration + dark panel + Poppins title.

    size="desktop" -> 1200x629, size="mobile" -> 450x236.
    All geometry scales from the 1200x630 reference design.
    """
    W, H = SIZES.get(size, SIZES["desktop"])
    fonts = ensure_fonts()
    canvas = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(canvas)
    panel, accent = theme["panel"], theme["accent"]
    s = H / 630  # scale factor vs the reference design

    def sc(v, minimum=1):
        return max(minimum, int(round(v * s)))

    if layout == "right":  # <-- matches your reference image (half-half)
        # desktop keeps the approved 62.5/37.5 split, mobile uses 55/45
        ill_w = int(W * (0.625 if size == "desktop" else 0.55))
        canvas.paste(crop_fill(illustration, ill_w, H), (0, 0))
        d.rectangle([ill_w, 0, W, H], fill=panel)
        d.rectangle([ill_w, 0, ill_w + sc(8), H], fill=accent)   # accent edge
        pad = sc(36)
        x0, x1 = ill_w + pad, W - pad
        d.rounded_rectangle([x0, sc(148), x0 + sc(66), sc(160)],
                            radius=sc(6), fill=accent)
        if subtitle:
            y0, box_h = sc(180), sc(460) - sc(180)
        else:
            y0, box_h = sc(190), sc(500) - sc(190)
        draw_wrapped_title(d, title, (x0, y0, x1, y0 + box_h),
                           fonts["bold"], sc(62, 14), sc(30, 10), "white")
        if subtitle:
            sf = ImageFont.truetype(fonts["regular"], sc(26, 10))
            d.text((x0, y0 + box_h + sc(16)), subtitle,
                   font=sf, fill=(200, 210, 225))
    else:  # title strip along the bottom
        ill_h = int(H * 0.635)
        canvas.paste(crop_fill(illustration, W, ill_h), (0, 0))
        d.rectangle([0, ill_h, W, H], fill=panel)
        pad = sc(60)
        d.rounded_rectangle([pad, ill_h + sc(40), pad + sc(66), ill_h + sc(52)],
                            radius=sc(6), fill=accent)
        y0 = ill_h + sc(70)
        draw_wrapped_title(d, title, (pad, y0, W - pad, H - sc(24)),
                           fonts["bold"], sc(54, 14), sc(28, 10), "white")
    return canvas


# ------------------------------------------------------------------ batch ---
def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[: 50] or "image"


def generate_batch(title, theme_id="navy", variants=3, layout="right", subtitle="",
                   visual_hint=None, base_seed=None, provider="pollinations",
                   size=1024, model="flux", api_key=None, custom_image=None,
                   out_dir=None, sizes=("desktop",)):
    """Generate `variants` finished graphics in each requested output size.
    Returns list of saved paths."""
    theme = THEME_MAP.get(theme_id, THEME_MAP["navy"])
    out_dir = out_dir or OUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    sizes = [s for s in sizes if s in SIZES] or ["desktop"]
    prompt = build_prompt(title, theme, visual_hint)
    base_seed = base_seed if base_seed is not None else int.from_bytes(
        os.urandom(4), "big") % 100000

    paths = []
    for i in range(variants):
        seed = base_seed + i
        if custom_image is not None:
            ill = custom_image.convert("RGB")
        else:
            ill = generate_illustration(prompt, seed, provider=provider,
                                        size=size, model=model, api_key=api_key)
        for size_name in sizes:  # one illustration, rendered at every size
            final = compose(title, ill, theme, layout=layout,
                            subtitle=subtitle, size=size_name)
            fname = f"{slugify(title)}_{theme_id}_{size_name}_{seed}.png"
            path = os.path.join(out_dir, fname)
            final.save(path)
            paths.append(path)
    return paths, prompt
