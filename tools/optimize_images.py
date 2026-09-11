#!/usr/bin/env python3
"""
Download every image this site uses from the old WordPress site, convert it to
responsive WebP, and rewrite the HTML to use the local copies.

Run this ONCE before you switch the domain from WordPress to the static site
(after the switch, the old /wp-content/ image URLs will no longer exist).

    pip install pillow
    python tools/optimize_images.py                  # images used on the pages
    python tools/optimize_images.py --full-gallery   # also pull ALL gallery pages (~450 photos)

Run from the site root (the folder that contains index.html).
"""
import argparse, hashlib, html, os, re, sys, time, urllib.request
from io import BytesIO

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("Pillow is required:  pip install pillow")

ORIGIN = "https://www.slaunchedguideservice.com"
IMG_DIR = "assets/img"
URL_RE = None  # set in main()
WIDTHS = (480, 960, 1600)
UA = {"User-Agent": "Mozilla/5.0 (site-migration image optimizer)"}


def fetch(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except Exception as ex:  # noqa
            if i == tries - 1:
                print(f"  ! failed {url}: {ex}")
                return None
            time.sleep(1.5 * (i + 1))


def slug(url):
    base = os.path.splitext(os.path.basename(url.split("?")[0]))[0]
    base = re.sub(r"[^A-Za-z0-9_-]+", "-", base)[:60].strip("-") or "img"
    return f"{base}-{hashlib.md5(url.encode()).hexdigest()[:6]}"


def open_img(data):
    im = Image.open(BytesIO(data))
    im = ImageOps.exif_transpose(im)  # phone photos: fix rotation
    return im.convert("RGB")


def save_webp(im, w, path, q=74):
    if im.width > w:
        im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    im.save(path, "WEBP", quality=q, method=6)
    return im.size


class Store:
    """Downloads + converts each URL once; remembers generated variants."""
    def __init__(self):
        self.cache = {}

    def get(self, url, widths=None):
        if url in self.cache:
            return self.cache[url]
        print("  ↓", url.replace(ORIGIN, ""))
        data = fetch(url)
        if not data:
            self.cache[url] = None
            return None
        im = open_img(data)
        name = slug(url)
        out = {"w": im.width, "h": im.height, "variants": []}
        is_thumb = "/cache/" in url  # NextGEN 400x300 thumbnails
        ws = widths or WIDTHS
        widths = (im.width,) if is_thumb else tuple(w for w in ws if w < im.width) + (min(im.width, ws[-1]),)
        for w in sorted(set(widths)):
            fn = f"{IMG_DIR}/{name}-{w}.webp"
            size = save_webp(im, w, fn)
            out["variants"].append((fn, size))
        self.cache[url] = out
        return out


def scrape_gallery():
    """Return list of (thumb, full) for every NextGEN gallery page."""
    pairs, page = [], 1
    pat = re.compile(r'href="(' + re.escape(ORIGIN) + r'/wp-content/gallery/[^"]+?)"[^>]*>\s*<img[^>]+src="(' + re.escape(ORIGIN) + r'/wp-content/gallery/[^"]+/cache/[^"]+)"', re.S)
    while True:
        url = f"{ORIGIN}/gallery/" if page == 1 else f"{ORIGIN}/gallery/nggallery/page/{page}"
        print(f"  gallery page {page}")
        data = fetch(url)
        if not data:
            break
        found = [(t, f) for f, t in pat.findall(data.decode("utf-8", "ignore"))]
        new = [p for p in found if p not in pairs]
        if not new:
            break
        pairs += new
        page += 1
        if page > 60:
            break
    return pairs


def rebuild_gallery(pairs):
    fp = "gallery/index.html"
    s = open(fp, encoding="utf-8").read()
    cells = []
    for i, (t, f) in enumerate(pairs):
        cells.append(f'<a href="{f}" data-lb{" hidden" if i >= 24 else ""}><img src="{t}" '
                     f'alt="Trophy bass caught with Slaunched Guide Service, photo {i+1}" width="400" height="300" '
                     f'loading="lazy" decoding="async"></a>')
    s = re.sub(r"<!--GALLERY-START-->.*?<!--GALLERY-END-->",
               "<!--GALLERY-START-->" + "".join(cells) + "<!--GALLERY-END-->", s, flags=re.S)
    open(fp, "w", encoding="utf-8").write(s)
    print(f"  gallery now has {len(pairs)} photos")


def rewrite(fp, store, sizes_for):
    s = open(fp, encoding="utf-8").read()

    # <img ... src="REMOTE" ...>  -> local src + srcset + real width/height
    def img_tag(m):
        tag = m.group(0)
        src = re.search(r'src="([^"]+)"', tag).group(1)
        if not URL_RE.match(src + "\""):
            return tag
        logo = "logo" in tag.lower()
        info = store.get(src, (150, 300) if logo else None)
        if not info:
            return tag
        vs = info["variants"]
        if logo:
            tag = tag.replace(f'src="{src}"', f'src="/{vs[0][0]}"')
            if len(vs) > 1:
                tag = tag.replace("<img ", f'<img srcset="/{vs[0][0]} 1x, /{vs[-1][0]} 2x" ', 1)
            return tag
        best = vs[-1] if len(vs) == 1 else next((v for v in vs if v[1][0] >= 960), vs[-1])
        tag = tag.replace(f'src="{src}"', f'src="/{best[0]}"')
        if len(vs) > 1:
            srcset = ", ".join(f"/{fn} {w}w" for fn, (w, h) in vs)
            tag = tag.replace("<img ", f'<img srcset="{srcset}" sizes="{sizes_for(tag)}" ', 1)
        w, h = best[1]
        tag = re.sub(r'width="\d+"', f'width="{w}"', tag)
        tag = re.sub(r'height="\d+"', f'height="{h}"', tag)
        return tag
    s = re.sub(r"<img\b[^>]*>", img_tag, s)

    # hero preload -> matching responsive preload
    def preload(m):
        url = m.group(1)
        info = store.get(url)
        if not info:
            return m.group(0)
        vs = info["variants"]
        srcset = ", ".join(f"/{fn} {w}w" for fn, (w, h) in vs)
        return (f'<link rel="preload" as="image" href="/{vs[-1][0]}" imagesrcset="{srcset}" '
                f'imagesizes="100vw" fetchpriority="high">')
    s = re.sub(r'<link rel="preload" as="image" href="(' + URL_RE.pattern + r')" fetchpriority="high">', preload, s)

    # hrefs (lightbox full-size, downloads, favicons) -> largest local webp
    def href(m):
        attr, url = m.group(1), m.group(2)
        info = store.get(url)
        if not info:
            return m.group(0)
        return f'{attr}="/{info["variants"][-1][0]}"'
    s = re.sub(r'\b(href)="(' + URL_RE.pattern + r')"', href, s)

    # og:image + JSON-LD image/logo -> absolute URL of a local JPEG
    def absolute(m):
        url = m.group(0)
        name = slug(url)
        jpg = f"{IMG_DIR}/{name}-og.jpg"
        if not os.path.exists(jpg):
            data = fetch(url)
            if not data:
                return url
            im = open_img(data)
            if im.width > 1200:
                im = im.resize((1200, round(im.height * 1200 / im.width)), Image.LANCZOS)
            im.save(jpg, "JPEG", quality=82, optimize=True, progressive=True)
        return f"{ORIGIN}/{jpg}"
    s = re.sub(URL_RE.pattern, absolute, s)

    s = s.replace(f'<link rel="preconnect" href="{ORIGIN}" crossorigin>\n', "")
    open(fp, "w", encoding="utf-8").write(s)


def main():
    global URL_RE
    ap = argparse.ArgumentParser()
    ap.add_argument("--full-gallery", action="store_true", help="scrape every gallery page from the WordPress site")
    ap.add_argument("--origin", default=ORIGIN, help=argparse.SUPPRESS)
    a = ap.parse_args()
    globals()["ORIGIN"] = a.origin.rstrip("/")
    URL_RE = re.compile(re.escape(ORIGIN) + r"/wp-content/[^\"'\s<>)]+?\.(?:jpe?g|png|webp|gif)(?=[\"'\s<>)])", re.I)
    if not os.path.exists("index.html"):
        sys.exit("Run this from the site root folder (where index.html is).")
    os.makedirs(IMG_DIR, exist_ok=True)

    if a.full_gallery:
        print("Scraping full gallery…")
        pairs = scrape_gallery()
        if pairs:
            rebuild_gallery(pairs)

    def sizes_for(tag):
        if 'fetchpriority="high"' in tag:
            return "100vw"
        if 'width="400"' in tag:
            return "(max-width: 600px) 50vw, 300px"
        return "(max-width: 880px) 100vw, 580px"

    store = Store()
    pages = [os.path.join(r, f) for r, _, fs in os.walk(".") for f in fs if f.endswith(".html") and "tools" not in r]
    for fp in sorted(pages):
        print("Processing", fp)
        rewrite(fp, store, sizes_for)

    left = [p for p in pages if URL_RE.search(open(p, encoding="utf-8").read().replace(ORIGIN + "/" + IMG_DIR, ""))]
    total = sum(os.path.getsize(os.path.join(IMG_DIR, f)) for f in os.listdir(IMG_DIR))
    print(f"\nDone. {len(os.listdir(IMG_DIR))} files, {total/1e6:.1f} MB in {IMG_DIR}/")
    if left:
        print("Some remote images could not be downloaded; they are still linked remotely in:", *left, sep="\n  ")


if __name__ == "__main__":
    main()
