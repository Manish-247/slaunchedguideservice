# Slaunched Guide Service – static HTML site

Hand-built static version of slaunchedguideservice.com. No WordPress, no jQuery, no page builder:
inline CSS (~9 KB), one 3 KB deferred script, one self-hosted font (22 KB).

## Pages (same URLs as the WordPress site, so Google rankings carry over)
/  ·  /about-us/  ·  /pricing/  ·  /gallery/  ·  /pro-bass-adventures-mexico/  ·  /contact/  ·  /booking/  ·  /404.html

## IMPORTANT: run the image step before going live
Right now the pages load photos straight from the old WordPress `/wp-content/` folder.
Once the domain points at this static site, those URLs will stop working. Run this once,
while WordPress is still online:

    pip install pillow
    cd slaunched-site
    python tools/optimize_images.py --full-gallery

It downloads every photo, fixes phone-photo rotation, converts to WebP in 480/960/1600 px
sizes, adds `srcset` so phones get small files, and rewrites all HTML to local
`/assets/img/` paths. `--full-gallery` also pulls all ~19 gallery pages (~450 photos) into
/gallery/ (24 shown at first, "Show more photos" reveals the rest). Omit it to keep the 48 included.

## Preview locally
Links use root paths (/pricing/), so open it through a tiny server, not by double-clicking:

    python -m http.server 8000     # then visit http://localhost:8000

## Hosting
Any static host works: Netlify, Cloudflare Pages, Vercel, GitHub Pages, or your current cPanel
(upload the folder contents to public_html). `.htaccess` (Apache/cPanel) and `_headers`
(Netlify/Cloudflare) turn on compression + 1-year image caching, which PageSpeed checks for.

## Booking form
With no server, the form opens the visitor's email app with the trip details filled in,
addressed to christiangladfelter10@gmail.com. To receive submissions directly instead,
create a free Formspree form and add `action="https://formspree.io/f/XXXX" method="POST"`
to `<form id="book">` in /booking/index.html.

## SEO included
Unique titles + meta descriptions, canonical tags, Open Graph, LocalBusiness / Service /
TouristTrip / Breadcrumb structured data, sitemap.xml, robots.txt, descriptive alt text,
semantic headings. After launch, submit sitemap.xml in Google Search Console.
