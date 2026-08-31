#!/usr/bin/env python3
"""Generate the flowlabapps.com static site from _build/apps.json.

Usage:  python3 _build/build.py

Everything under the repo root except _build/ and .git/ is generated output.
Add an app by adding an entry to apps.json and re-running this script.
"""

import base64
import hashlib
import html
import json
import os
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "_build", "apps.json")

with open(DATA, encoding="utf-8") as fh:
    CONFIG = json.load(fh)

ICON_SRC = os.path.join(ROOT, "_build", "icons")

# The real App Store / Play icon for each app, downscaled and committed under
# _build/icons/. Any app without one falls back to its drawn mark below, so a
# new app can be added to the site before its artwork exists.
APP_ART = {}
if os.path.isdir(ICON_SRC):
    for _f in sorted(os.listdir(ICON_SRC)):
        _slug, _dot, _ext = _f.rpartition(".")
        if _ext.lower() in ("png", "jpg", "jpeg", "webp"):
            APP_ART[_slug] = _f

SITE = CONFIG["site"]
APPS = CONFIG["apps"]
EMAIL = SITE["email"]
COMPANY = SITE["company"]
UPDATED = SITE["updated"]

STATUS_LABEL = {
    "live": "Available",
    "soon": "Coming soon",
    "dev": "In development",
}


def e(text):
    """Escape text for HTML."""
    return html.escape(str(text), quote=False)


def md_inline(text):
    """Minimal inline markdown: **bold** and `code`."""
    text = e(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


def write(relpath, content):
    """Write a file, rewriting site-root-relative links to page-relative ones.

    Templates below are authored with root-relative URLs (`href="/support/"`,
    `src="/assets/icons/x.png"`). Those only resolve when the site is served from
    a domain root, so they break when a page is opened straight from Finder over
    file:// or hosted under a subpath. Here they are converted to the correct
    number of `../` hops for the page's own depth, which resolves identically in
    all three cases. Absolute (https:), mailto: and #fragment URLs are left alone.
    """
    depth = relpath.count("/")
    prefix = "../" * depth if depth else "./"
    for attr in ("href", "src"):
        content = content.replace(f'{attr}="/', f'{attr}="{prefix}')

    # Cloudflare's Email Address Obfuscation rewrites every mailto: link into a
    # /cdn-cgi/l/email-protection URL whose text only resolves once
    # email-decode.min.js runs. Our CSP allows exactly one script hash and no
    # host sources, so that script is blocked and the contact address renders
    # as the literal string "[email protected]" — a dead end for anyone trying
    # to reach support, App Review included. These markers tell Cloudflare to
    # leave the address alone.
    content = re.sub(r'(<a\b[^>]*href="mailto:[^"]*"[^>]*>.*?</a>)',
                     r'<!--email_off-->\1<!--/email_off-->',
                     content, flags=re.S)

    path = os.path.join(ROOT, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return relpath


# --------------------------------------------------------------------------
# Shared chrome
# --------------------------------------------------------------------------

def page(title, description, body, accent=None, extra_head="", canonical=None):
    a1, a2 = accent or ("#7a63ff", "#00d1ff")
    canon = ""
    if canonical:
        canon = (f'<link rel="canonical" href="https://{SITE["domain"]}{canonical}" />\n'
                 f'<meta property="og:url" content="https://{SITE["domain"]}{canonical}" />\n')
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>{e(title)}</title>
<meta name="description" content="{html.escape(description, quote=True)}" />
<meta name="theme-color" content="#07080c" />
<meta name="color-scheme" content="dark" />
{canon}<meta property="og:title" content="{html.escape(title, quote=True)}" />
<meta property="og:description" content="{html.escape(description, quote=True)}" />
<meta property="og:site_name" content="{html.escape(COMPANY, quote=True)}" />
<meta property="og:type" content="website" />
<meta name="twitter:card" content="summary" />
<link rel="icon" href="/favicon.svg" type="image/svg+xml" />
<link rel="stylesheet" href="/assets/site.css" />
<style>:root{{--a1:{a1};--a2:{a2}}}</style>
{extra_head}</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="wrap">
{nav()}
<main id="main">
{body}
</main>
{footer()}
</div>
</body>
</html>
"""


def nav():
    return """<header class="nav">
  <a class="brand" href="/"><span class="dot" aria-hidden="true"></span> Flowlab Apps</a>
  <nav class="navlinks" aria-label="Main">
    <a href="/#apps">Apps</a>
    <a href="/support/">Support</a>
    <a href="/privacy/">Privacy</a>
  </nav>
</header>"""


def footer():
    links = "\n".join(
        f'        <a href="/apps/{a["slug"]}/">{e(a["name"])}</a>' for a in APPS
    )
    return f"""<footer>
  <div class="footgrid">
    <div class="footbrand">
      <a class="brand" href="/"><span class="dot" aria-hidden="true"></span> {e(COMPANY)}</a>
      <p>Focused apps and games for iPhone, iPad, Android and Mac. No accounts, no analytics,
      no ads — your data stays on your device.</p>
    </div>
    <div>
      <div class="footlabel">Apps</div>
      <div class="footlinks">
{links}
      </div>
    </div>
    <div>
      <div class="footlabel">Company</div>
      <div class="footlinks">
        <a href="/support/">Support</a>
        <a href="/privacy/">Privacy Policy</a>
        <a href="/terms/">Terms of Use</a>
        <a href="/data-deletion/">Data &amp; Account Deletion</a>
        <a href="/kids/">Children's Privacy</a>
        <a href="/accessibility/">Accessibility</a>
        <a href="/security/">Security</a>
        <a href="mailto:{EMAIL}">{EMAIL}</a>
      </div>
    </div>
  </div>
  <div class="footnote">© {SITE["copyright_year"]} {e(COMPANY)}. All rights reserved.
  Apple, App Store, iPhone, iPad, macOS and Apple Health are trademarks of Apple Inc.
  Google Play and Android are trademarks of Google LLC.</div>
</footer>"""


def status_badge(app):
    kind = app.get("status_kind", "dev")
    return f'<span class="badge badge-{kind}">{e(app["status"])}</span>'


def platform_pills(app):
    return "".join(f'<span class="pill">{e(p)}</span>' for p in app["platforms"])


# --------------------------------------------------------------------------
# App marks
#
# One hand-drawn line mark per app, on a 24x24 grid. These replace the single
# Unicode glyphs the first version used: a stroked mark scales cleanly to any
# size, renders identically on every platform, and never falls back to a colour
# emoji font the way a character like the tornado glyph did.
# --------------------------------------------------------------------------

MARKS = {
    # Fasting ring closing in on its goal.
    "pulsefast": ('<circle cx="12" cy="12" r="8.6" opacity=".32"/>'
                  '<path d="M12 3.4a8.6 8.6 0 0 1 7.7 12.4"/>'
                  '<circle cx="12" cy="12" r="2.5" fill="currentColor" stroke="none"/>'),
    # Capture frame with a selection inside it.
    "lucidframe": ('<path d="M4 8.6V6.2A2.2 2.2 0 0 1 6.2 4h2.4M15.4 4h2.4A2.2 2.2 0 0 1 20 6.2v2.4'
                   'M20 15.4v2.4a2.2 2.2 0 0 1-2.2 2.2h-2.4M8.6 20H6.2A2.2 2.2 0 0 1 4 17.8v-2.4"/>'
                   '<rect x="8.4" y="8.4" width="7.2" height="7.2" rx="1.6" opacity=".55"/>'),
    # Editor prompt: chevron and a caret rule.
    "syntaxpad": ('<rect x="3" y="4.2" width="18" height="15.6" rx="3.2" opacity=".38"/>'
                  '<path d="m7.6 9.2 3.2 2.9-3.2 2.9"/><path d="M13.4 15h3.4"/>'),
    # Singularity with an accretion disc.
    "black-hole-rush": ('<circle cx="12" cy="12" r="3.9" fill="currentColor" stroke="none"/>'
                        '<ellipse cx="12" cy="12" rx="9" ry="3.9"/>'
                        '<ellipse cx="12" cy="12" rx="9" ry="3.9" transform="rotate(-32 12 12)" opacity=".38"/>'),
    # Funnel, tapering downward.
    "twister-rush": ('<ellipse cx="12" cy="5.6" rx="7.2" ry="2.5"/>'
                     '<ellipse cx="12" cy="12" rx="4.5" ry="1.7" opacity=".7"/>'
                     '<ellipse cx="12" cy="17.8" rx="2.1" ry="1" opacity=".5"/>'),
    # Heading arrow.
    "city-rush": '<path d="M12 3.4 19.2 20 12 16.3 4.8 20z" stroke-linejoin="round"/>',
    # House.
    "dream-home-adventures": ('<path d="M3.8 10.4 12 3.8l8.2 6.6v7.9a1.9 1.9 0 0 1-1.9 1.9H5.7a1.9 1.9 0 0 1-1.9-1.9z"/>'
                              '<path d="M9.6 20.2v-5.1h4.8v5.1" opacity=".6"/>'),
    # Document with a keyhole.
    "keyclave": ('<path d="M6.2 3.6h7.3L18 8.1v12.3H6.2z"/>'
                 '<path d="M13.5 3.6v4.5H18" opacity=".6"/>'
                 '<circle cx="12.1" cy="12.9" r="1.7"/><path d="M12.1 14.6v2.6"/>'),
    # Shield with a keyhole.
    "keybound": ('<path d="M12 3.2 19 6.1v5.9c0 4.2-2.9 7.4-7 8.8-4.1-1.4-7-4.6-7-8.8V6.1z"/>'
                 '<circle cx="12" cy="11" r="1.8"/><path d="M12 12.8v2.7"/>'),
    # Remote handset.
    "universal-remote": ('<rect x="7" y="3" width="10" height="18" rx="3.2"/>'
                         '<circle cx="12" cy="7.4" r="1.4"/>'
                         '<path d="M9.6 12h4.8M9.6 15.6h4.8" opacity=".6"/>'),
}

ARROW = ('<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" '
         'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
         '<path d="M3 8h10M9 4l4 4-4 4"/></svg>')

BACK_ARROW = ('<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" '
              'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
              '<path d="M13 8H3M7 4 3 8l4 4"/></svg>')


def app_icon(app, size="md", eager=False):
    """The app's real store icon, or its drawn mark if there is no artwork yet.

    The accent pair is set either way: on the art variant it tints the drop
    shadow under the tile, so each icon keeps its own glow.
    """
    c1, c2 = app["accent"]
    art = APP_ART.get(app["slug"])
    if art:
        load = "eager" if eager else "lazy"
        return (f'<span class="icon icon-{size} has-art" style="--c1:{c1};--c2:{c2}" aria-hidden="true">'
                f'<img src="/assets/icons/{art}" alt="" width="256" height="256" '
                f'loading="{load}" decoding="async" /></span>')
    mark = MARKS.get(app["slug"], MARKS["syntaxpad"])
    return (f'<span class="icon icon-{size}" style="--c1:{c1};--c2:{c2}" aria-hidden="true">'
            f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
            f'stroke-linecap="round" stroke-linejoin="round">{mark}</svg></span>')


def app_header(app, section=None):
    """Shared masthead for every page belonging to one app."""
    here = section or "Overview"
    crumb = ""
    if section:
        crumb = f' <span class="sep">/</span> <span class="crumb-here">{e(section)}</span>'

    def link(label, href):
        cur = ' aria-current="page"' if label == here else ""
        return f'    <a href="{href}"{cur}>{label}</a>'

    links = "\n".join([
        link("Overview", f"/apps/{app['slug']}/"),
        link("Support", f"/apps/{app['slug']}/support/"),
        link("Privacy", f"/apps/{app['slug']}/privacy/"),
    ])
    return f"""<div class="appbar">
  <div class="appbar-id">
    {app_icon(app, "sm")}
    <div>
      <div class="crumb"><a href="/apps/{app["slug"]}/">{e(app["name"])}</a>{crumb}</div>
      <div class="appbar-tag">{e(app["tagline"])}</div>
    </div>
  </div>
  <div class="appbar-links">
{links}
  </div>
</div>"""


def back_to_apps():
    return f'<a class="backlink" href="/#apps">{BACK_ARROW} All apps</a>'


def is_game(app):
    return app["category"].lower().startswith("games")


# --------------------------------------------------------------------------
# Stylesheet
# --------------------------------------------------------------------------

CSS = """
/* ==========================================================================
   Flowlab Apps — design system
   Dark, quiet, accent-tinted per page. No web fonts: the whole site loads
   from one origin, which is the same promise the apps make.
   ========================================================================== */

:root{
  --bg:#07080c;
  --text:#f3f4f8;
  --muted:#a8adbd;
  --faint:#767c90;
  --line:rgba(255,255,255,.085);
  --line-2:rgba(255,255,255,.16);
  --r:20px;
  --r-sm:14px;
  --maxw:1160px;
  --a1:#7a63ff; --a2:#00d1ff;
  --ease:cubic-bezier(.2,.7,.3,1);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth; -webkit-text-size-adjust:100%}
body{
  margin:0; color:var(--text);
  font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",Roboto,Helvetica,Arial,system-ui,sans-serif;
  font-size:16px; line-height:1.6; letter-spacing:-.006em;
  background:var(--bg);
  min-height:100vh;
  -webkit-font-smoothing:antialiased; -moz-osx-font-smoothing:grayscale;
  font-variant-numeric:tabular-nums;
}
/* Ambient accent field. Fixed, so it does not travel with the scroll. */
body::before{
  content:""; position:fixed; inset:0; z-index:-2; pointer-events:none;
  background:
    radial-gradient(1000px 620px at 8% -12%, color-mix(in srgb, var(--a1) 26%, transparent), transparent 60%),
    radial-gradient(900px 560px at 96% -6%, color-mix(in srgb, var(--a2) 17%, transparent), transparent 58%),
    radial-gradient(1200px 700px at 50% 108%, color-mix(in srgb, var(--a1) 9%, transparent), transparent 62%);
}
/* Fine grain, so large flat panels do not band on wide displays. */
body::after{
  content:""; position:fixed; inset:0; z-index:-1; pointer-events:none; opacity:.028;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}
a{color:inherit; text-decoration:none}
.prose a{text-decoration:underline; text-underline-offset:3px; text-decoration-thickness:1px; text-decoration-color:var(--line-2)}
.prose a:hover{text-decoration-color:currentColor}
.skip{position:absolute;left:-9999px}
.skip:focus{left:14px;top:14px;z-index:99;background:#fff;color:#000;padding:10px 14px;border-radius:10px;font-weight:650}
:focus-visible{outline:2px solid var(--a2); outline-offset:3px; border-radius:8px}
::selection{background:color-mix(in srgb, var(--a1) 45%, transparent)}
.wrap{max-width:var(--maxw); margin:0 auto; padding:20px 20px 64px}
@media (max-width:600px){ .wrap{padding:14px 14px 44px} }

/* --- nav ---------------------------------------------------------------- */
.nav{
  display:flex; align-items:center; justify-content:space-between; gap:12px;
  padding:9px 10px 9px 16px; border:1px solid var(--line); border-radius:999px;
  background:color-mix(in srgb, var(--bg) 72%, transparent);
  backdrop-filter:blur(18px) saturate(160%); -webkit-backdrop-filter:blur(18px) saturate(160%);
  position:sticky; top:14px; z-index:30;
  box-shadow:0 1px 0 0 rgba(255,255,255,.05) inset, 0 12px 34px -18px #000;
}
.brand{display:flex; align-items:center; gap:10px; font-weight:680; letter-spacing:-.01em}
.brand .dot{
  width:20px;height:20px;border-radius:7px;flex:none;
  background:linear-gradient(140deg,var(--a1),var(--a2));
  box-shadow:0 3px 10px -2px color-mix(in srgb, var(--a1) 70%, transparent), inset 0 1px 0 rgba(255,255,255,.45);
}
.navlinks{display:flex; gap:2px; color:var(--muted); font-size:14px}
.navlinks a{padding:8px 13px; border-radius:999px; transition:background .18s var(--ease), color .18s var(--ease)}
.navlinks a:hover{background:rgba(255,255,255,.07); color:var(--text)}
@media (max-width:600px){
  .nav{padding:8px 8px 8px 13px; gap:6px; top:10px}
  .brand{font-size:14.5px; white-space:nowrap; gap:8px}
  .brand .dot{width:17px;height:17px;border-radius:6px}
  .navlinks{font-size:13px; gap:0}
  .navlinks a{padding:7px 9px}
}

/* --- surfaces ----------------------------------------------------------- */
.card{
  position:relative; isolation:isolate;
  border:1px solid var(--line); border-radius:var(--r);
  background:linear-gradient(180deg, rgba(255,255,255,.055), rgba(255,255,255,.022));
  box-shadow:inset 0 1px 0 rgba(255,255,255,.07), 0 34px 64px -40px #000;
  padding:30px; margin-top:18px;
}
@media (max-width:600px){ .card{padding:20px; margin-top:14px; border-radius:16px} }

h1{margin:0 0 14px; font-size:clamp(30px,5.2vw,46px); line-height:1.05; letter-spacing:-.032em; font-weight:700}
h2{margin:0 0 12px; font-size:clamp(21px,2.6vw,27px); line-height:1.18; letter-spacing:-.022em; font-weight:680}
h3{margin:24px 0 8px; font-size:17px; letter-spacing:-.012em; font-weight:660}
p{margin:0 0 13px; color:var(--muted)}
p:last-child{margin-bottom:0}
.lede{font-size:clamp(16px,1.6vw,18.5px); line-height:1.62; color:#c9cdda; letter-spacing:-.01em}
.kicker{
  display:inline-flex; align-items:center; gap:8px; margin-bottom:12px;
  font-size:11.5px; letter-spacing:.16em; text-transform:uppercase; font-weight:660; color:var(--faint);
}
.kicker::before{content:""; width:14px; height:1px; background:var(--line-2)}
ul,ol{margin:12px 0 0; padding-left:20px; color:var(--muted)}
li{margin:7px 0}
li::marker{color:var(--faint)}
code{background:rgba(255,255,255,.07); border:1px solid var(--line); padding:1px 6px; border-radius:6px;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.86em}
strong{color:var(--text); font-weight:650}
hr{border:0;border-top:1px solid var(--line);margin:26px 0}

/* --- app icons ---------------------------------------------------------- */
.icon{
  position:relative; display:grid; place-items:center; flex:none; color:#fff;
  background:linear-gradient(148deg, var(--c1,var(--a1)), var(--c2,var(--a2)));
  border-radius:24%;
  box-shadow:
    inset 0 0 0 1px rgba(255,255,255,.14),
    inset 0 1.5px 0 rgba(255,255,255,.4),
    0 14px 30px -12px color-mix(in srgb, var(--c1,var(--a1)) 75%, transparent);
}
.icon::after{
  content:""; position:absolute; inset:0; border-radius:inherit; pointer-events:none;
  background:linear-gradient(180deg, rgba(255,255,255,.26), rgba(255,255,255,0) 52%, rgba(0,0,0,.12));
}
.icon svg{width:56%; height:56%; position:relative; z-index:1; filter:drop-shadow(0 1.5px 2px rgba(0,0,0,.28))}
/* Real store artwork: no gradient behind it and no heavy gloss over it — just
   the rounded mask, a hairline edge and the accent-tinted shadow. */
.icon.has-art{background:none; box-shadow:0 14px 30px -12px color-mix(in srgb, var(--c1) 62%, transparent)}
.icon.has-art img{width:100%; height:100%; border-radius:inherit; display:block; object-fit:cover}
.icon.has-art::after{
  background:linear-gradient(180deg, rgba(255,255,255,.08), rgba(255,255,255,0) 46%);
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.14);
}
.icon-sm{width:38px;height:38px}
.icon-md{width:56px;height:56px}
.icon-lg{width:72px;height:72px}
.icon-xl{width:96px;height:96px}
@media (max-width:600px){ .icon-xl{width:76px;height:76px} .icon-lg{width:62px;height:62px} }

/* --- pills, badges ------------------------------------------------------ */
.pill{
  display:inline-block; border:1px solid var(--line); background:rgba(255,255,255,.045);
  padding:5px 12px; border-radius:999px; font-size:12.5px; color:var(--muted); margin:0 6px 6px 0;
}
.badge{display:inline-flex; align-items:center; gap:6px; padding:4px 11px; border-radius:999px;
  font-size:11.5px; font-weight:660; letter-spacing:.01em; white-space:nowrap}
.badge::before{content:""; width:5px; height:5px; border-radius:50%; background:currentColor}
.badge-live{background:rgba(52,211,153,.13); color:#5eead4; border:1px solid rgba(52,211,153,.3)}
.badge-soon{background:rgba(251,191,36,.12); color:#fcd34d; border:1px solid rgba(251,191,36,.28)}
.badge-dev{background:rgba(255,255,255,.055); color:var(--faint); border:1px solid var(--line)}

/* --- hero --------------------------------------------------------------- */
.hero{padding:64px 30px 52px; text-align:center; overflow:hidden}
.hero .kicker{margin-inline:auto}
.hero h1{font-size:clamp(34px,6.4vw,64px); max-width:15ch; margin-inline:auto; letter-spacing:-.04em}
.hero .lede{max-width:58ch; margin:0 auto}
.hero .cta{justify-content:center; margin-top:26px}
@media (max-width:600px){ .hero{padding:40px 18px 34px} }
.gradtext{
  background:linear-gradient(104deg,var(--a1) 10%,var(--a2) 90%);
  -webkit-background-clip:text; background-clip:text; color:transparent;
}
.heroshelf{
  display:flex; justify-content:center; gap:10px; flex-wrap:wrap; margin-top:36px;
  padding-top:30px; border-top:1px solid var(--line);
}
.heroshelf a{
  display:block; border-radius:24%; transition:transform .22s var(--ease);
}
.heroshelf a:hover{transform:translateY(-5px) scale(1.05)}
@media (max-width:600px){ .heroshelf{gap:8px; margin-top:28px; padding-top:24px} }

/* --- app gallery -------------------------------------------------------- */
.filters{display:flex; gap:6px; flex-wrap:wrap; margin:18px 0 4px}
.filters button{
  font:inherit; font-size:13.5px; font-weight:600; color:var(--muted); cursor:pointer;
  border:1px solid var(--line); background:rgba(255,255,255,.035);
  padding:7px 15px; border-radius:999px; transition:.18s var(--ease);
}
.filters button:hover{background:rgba(255,255,255,.075); color:var(--text)}
.filters button[aria-pressed="true"]{
  color:var(--text); border-color:transparent;
  background:linear-gradient(135deg, color-mix(in srgb,var(--a1) 62%,transparent), color-mix(in srgb,var(--a2) 40%,transparent));
  box-shadow:inset 0 1px 0 rgba(255,255,255,.25);
}
.appgrid{display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-top:18px}
@media (max-width:920px){ .appgrid{grid-template-columns:repeat(2,1fr)} }
@media (max-width:620px){ .appgrid{grid-template-columns:1fr} }
.appgrid[data-filter="app"] .appcard[data-kind="game"],
.appgrid[data-filter="game"] .appcard[data-kind="app"]{display:none}

.appcard{
  position:relative; isolation:isolate; display:flex; flex-direction:column;
  border:1px solid var(--line); border-radius:18px; padding:22px;
  background:linear-gradient(180deg, rgba(255,255,255,.055), rgba(255,255,255,.02));
  transition:transform .22s var(--ease), border-color .22s var(--ease), box-shadow .22s var(--ease);
}
.appcard::before{
  content:""; position:absolute; inset:0; z-index:-1; border-radius:inherit; opacity:0;
  background:radial-gradient(420px 200px at 22% 0%, color-mix(in srgb, var(--c1) 22%, transparent), transparent 70%);
  transition:opacity .22s var(--ease);
}
.appcard:hover{
  transform:translateY(-4px);
  border-color:color-mix(in srgb, var(--c1) 42%, var(--line));
  box-shadow:0 26px 50px -30px #000, 0 0 0 1px color-mix(in srgb, var(--c1) 16%, transparent);
}
.appcard:hover::before{opacity:1}
.appcard .icon{margin-bottom:16px; transition:transform .22s var(--ease)}
.appcard:hover .icon{transform:scale(1.06) rotate(-2deg)}
.appcard h3{margin:0 0 5px; font-size:18.5px; color:var(--text); letter-spacing:-.018em}
.appcard .tag{color:#b4b9c9; font-size:13.5px; margin-bottom:11px; letter-spacing:-.005em}
.appcard p{font-size:14px; line-height:1.55; margin-bottom:16px; flex:1; color:var(--faint)}
.appcard .foot{display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap;
  margin-top:auto; padding-top:14px; border-top:1px solid var(--line)}
.appcard .plats{font-size:12px; color:var(--faint); letter-spacing:.01em}
.appcard .go{color:var(--muted)}
.appcard:hover .go{color:var(--text)}
.appcard:hover .go svg{transform:translateX(3px)}

/* --- inline arrows ------------------------------------------------------ */
.go{font-size:13px; font-weight:640; display:inline-flex; align-items:center; gap:6px; white-space:nowrap}
.go svg{width:13px; height:13px; flex:none; transition:transform .22s var(--ease)}
a.go:hover svg{transform:translateX(3px)}
.btn svg{width:15px; height:15px; flex:none}

/* --- app page hero ------------------------------------------------------ */
.apphero{display:flex; gap:26px; align-items:flex-start; padding:34px 30px}
.apphero .icon{margin-top:4px}
.apphero h1{margin:0 0 12px; font-size:clamp(30px,4.6vw,44px)}
@media (max-width:700px){ .apphero{flex-direction:column; gap:18px; padding:24px 20px} }

/* --- app-level bar ------------------------------------------------------ */
.appbar{
  display:flex; align-items:center; justify-content:space-between; gap:14px; flex-wrap:wrap;
  border:1px solid var(--line); border-radius:16px; background:rgba(255,255,255,.035);
  padding:11px 14px; margin-top:18px;
}
.appbar-id{display:flex; align-items:center; gap:13px; min-width:0}
.crumb{font-weight:670; font-size:15px; letter-spacing:-.012em}
.crumb .sep{color:var(--faint); font-weight:400; margin:0 5px}
.crumb-here{color:var(--muted); font-weight:600}
.appbar-tag{font-size:13px; color:var(--faint)}
.appbar-links{display:flex; gap:2px; font-size:13.5px; color:var(--muted)}
.appbar-links a{padding:7px 12px; border-radius:999px; transition:.18s var(--ease)}
.appbar-links a:hover{background:rgba(255,255,255,.07); color:var(--text)}
.appbar-links a[aria-current]{background:rgba(255,255,255,.09); color:var(--text)}
@media (max-width:600px){
  .appbar{padding:11px 12px; gap:10px}
  .appbar-links{font-size:13px; gap:0; margin-left:-9px}
  .appbar-links a{padding:6px 9px}
}
.backlink{display:inline-flex; align-items:center; gap:7px; font-size:13.5px; color:var(--faint); margin-bottom:14px}
.backlink:hover{color:var(--text)}
.backlink svg{width:13px;height:13px}

/* --- feature grid ------------------------------------------------------- */
.grid{display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-top:18px}
.grid.two{grid-template-columns:repeat(2,1fr)}
@media (max-width:900px){ .grid{grid-template-columns:repeat(2,1fr)} }
@media (max-width:640px){ .grid,.grid.two{grid-template-columns:1fr} }
.feat{
  border:1px solid var(--line); border-radius:var(--r-sm); padding:18px;
  background:rgba(255,255,255,.032); transition:background .2s var(--ease), border-color .2s var(--ease);
}
.feat:hover{background:rgba(255,255,255,.055); border-color:var(--line-2)}
.feat b{display:block; margin-bottom:7px; font-size:15px; font-weight:650; letter-spacing:-.012em}
.feat p{margin:0; font-size:14px; line-height:1.55; color:var(--faint)}
.feat .num{
  display:block; font-size:11px; letter-spacing:.14em; font-weight:660; margin-bottom:10px;
  color:transparent; background:linear-gradient(120deg,var(--a1),var(--a2));
  -webkit-background-clip:text; background-clip:text;
}

/* --- tables ------------------------------------------------------------- */
.tablewrap{overflow-x:auto; margin-top:18px; border:1px solid var(--line); border-radius:var(--r-sm)}
table{border-collapse:collapse; width:100%; min-width:520px; font-size:14.5px}
th,td{text-align:left; padding:12px 15px; border-bottom:1px solid var(--line); vertical-align:top}
th{font-size:11px; letter-spacing:.13em; text-transform:uppercase; color:var(--faint); font-weight:660;
   background:rgba(255,255,255,.028)}
td{color:var(--muted)}
td:first-child{color:var(--text)}
tr:last-child td{border-bottom:0}
.spec{min-width:0}
.spec th{width:34%; text-transform:none; letter-spacing:0; font-size:13.5px; background:none; color:var(--faint); font-weight:600}

/* --- callout ------------------------------------------------------------ */
.note{
  position:relative; border:1px solid var(--line); border-radius:var(--r-sm);
  background:linear-gradient(180deg, rgba(255,255,255,.055), rgba(255,255,255,.02));
  padding:16px 18px 16px 20px; margin:18px 0 0; overflow:hidden;
}
.note::before{content:""; position:absolute; left:0; top:0; bottom:0; width:3px;
  background:linear-gradient(180deg,var(--a1),var(--a2))}
.note p{margin:0; color:#c3c8d6}
.note b{color:var(--text)}

/* --- buttons ------------------------------------------------------------ */
.cta{display:flex; gap:10px; flex-wrap:wrap; margin-top:22px}
.btn{
  display:inline-flex; align-items:center; gap:8px; padding:11px 19px; border-radius:999px;
  font-weight:640; font-size:14.5px; letter-spacing:-.008em; border:1px solid var(--line-2);
  background:rgba(255,255,255,.055); color:var(--text);
  transition:transform .18s var(--ease), background .18s var(--ease), box-shadow .18s var(--ease);
}
.btn:hover{transform:translateY(-2px); background:rgba(255,255,255,.1)}
.btn.primary{
  border-color:transparent; color:#fff;
  background:linear-gradient(135deg, var(--a1), color-mix(in srgb, var(--a2) 82%, var(--a1)));
  box-shadow:inset 0 1px 0 rgba(255,255,255,.3), 0 12px 28px -14px color-mix(in srgb,var(--a1) 85%,transparent);
}
.btn.primary:hover{box-shadow:inset 0 1px 0 rgba(255,255,255,.3), 0 16px 34px -14px color-mix(in srgb,var(--a1) 90%,transparent)}

/* --- faq ---------------------------------------------------------------- */
details{border:1px solid var(--line); border-radius:var(--r-sm); padding:15px 17px;
  background:rgba(255,255,255,.03); margin-top:10px; transition:background .2s var(--ease)}
details[open]{background:rgba(255,255,255,.055)}
summary{cursor:pointer; font-weight:640; font-size:15px; list-style:none; display:flex; gap:12px;
  align-items:flex-start; letter-spacing:-.012em}
summary::-webkit-details-marker{display:none}
summary::before{content:"+"; color:var(--faint); font-weight:400; font-size:17px; line-height:1.35; flex:none}
details[open] summary::before{content:"\\2212"}
details p{margin:11px 0 0 25px; font-size:14.5px}

/* --- legal -------------------------------------------------------------- */
.legal h2{margin-top:34px; font-size:20px; padding-top:26px; border-top:1px solid var(--line)}
.legal h2:first-of-type{margin-top:20px; border-top:0; padding-top:0}
.legal h3{font-size:16px; margin-top:22px}
.legal p, .legal li{font-size:15px; line-height:1.7}
.meta-line{color:var(--faint); font-size:13.5px; margin-bottom:20px}
.toc{display:flex; flex-wrap:wrap; gap:7px; margin-top:16px}
.toc a{font-size:12.5px; color:var(--muted); border:1px solid var(--line); background:rgba(255,255,255,.035);
  padding:6px 13px; border-radius:999px; transition:.18s var(--ease)}
.toc a:hover{background:rgba(255,255,255,.08); color:var(--text)}

/* --- footer ------------------------------------------------------------- */
footer{margin-top:20px; padding:28px 30px; color:var(--muted); font-size:13.5px;
  border:1px solid var(--line); border-radius:var(--r); background:rgba(255,255,255,.022)}
@media (max-width:600px){ footer{padding:22px 20px} }
.footgrid{display:grid; grid-template-columns:1.4fr 1fr 1fr; gap:26px}
@media (max-width:760px){ .footgrid{grid-template-columns:1fr 1fr; gap:22px} }
@media (max-width:460px){ .footgrid{grid-template-columns:1fr} }
.footbrand p{font-size:13px; color:var(--faint); margin:12px 0 0; max-width:34ch}
.footlabel{font-size:11px; letter-spacing:.15em; text-transform:uppercase; color:var(--faint); margin-bottom:11px; font-weight:660}
.footlinks{display:flex; flex-direction:column; gap:7px}
.footlinks a{color:#b0b5c5; font-size:13.5px}
.footlinks a:hover{color:var(--text)}
.footnote{margin-top:26px; padding-top:18px; border-top:1px solid var(--line); color:var(--faint);
  font-size:12.5px; line-height:1.65}

@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{animation:none !important; transition:none !important}
  html{scroll-behavior:auto}
  .appcard:hover{transform:none}
  .heroshelf a:hover{transform:none}
}
"""


# --------------------------------------------------------------------------
# Home page
# --------------------------------------------------------------------------

HOME_JS = """
/* Progressive enhancement: without JS every app stays visible. */
(function () {
  var grid = document.getElementById('appgrid');
  if (!grid) return;
  var buttons = document.querySelectorAll('.filters button');
  Array.prototype.forEach.call(buttons, function (btn) {
    btn.addEventListener('click', function () {
      Array.prototype.forEach.call(buttons, function (b) {
        b.setAttribute('aria-pressed', String(b === btn));
      });
      grid.setAttribute('data-filter', btn.getAttribute('data-filter'));
    });
  });
})();
"""
HOME_SCRIPT = f"<script>{HOME_JS}</script>"


def build_home():
    shelf = "\n".join(
        f'    <a href="/apps/{a["slug"]}/" title="{html.escape(a["name"], quote=True)}" '
        f'aria-label="{html.escape(a["name"], quote=True)}">{app_icon(a, "md", eager=True)}</a>'
        for a in APPS
    )

    cards = []
    for a in APPS:
        c1, c2 = a["accent"]
        cards.append(f"""    <a class="appcard" href="/apps/{a['slug']}/"
       data-kind="{'game' if is_game(a) else 'app'}" style="--c1:{c1};--c2:{c2}">
      {app_icon(a, "lg")}
      <h3>{e(a['name'])}</h3>
      <div class="tag">{e(a['tagline'])}</div>
      <p>{e(a['summary'])}</p>
      <div class="foot">
        <span class="plats">{e(' · '.join(a['platforms']))}</span>
        {status_badge(a)}
      </div>
      <div class="foot" style="border:0;padding-top:10px">
        <span class="plats">{e(a['category'])}</span>
        <span class="go">View app {ARROW}</span>
      </div>
    </a>""")

    n_games = sum(1 for a in APPS if is_game(a))
    n_apps = len(APPS) - n_games

    body = f"""<section class="card hero">
  <div class="kicker">{e(COMPANY)}</div>
  <h1>Small apps that <span class="gradtext">keep your data</span> on your device.</h1>
  <p class="lede">We build focused tools and games for iPhone, iPad, Android and Mac.
  None of them have accounts. None of them run analytics. Most of them cannot reach the
  internet at all — and where one can, you are the one who asks it to.</p>
  <div class="cta">
    <a class="btn primary" href="#apps">Browse the apps {ARROW}</a>
    <a class="btn" href="/support/">Get support</a>
  </div>
  <div class="heroshelf">
{shelf}
  </div>
</section>

<section class="card" id="apps">
  <div class="kicker">Our apps</div>
  <h2>Pick an app to see what it does</h2>
  <p>Every app has its own page, its own support contact and its own privacy policy — the
  exact URLs published on its App Store and Google Play listing.</p>
  <div class="filters" role="group" aria-label="Filter apps by type">
    <button type="button" data-filter="all" aria-pressed="true">All {len(APPS)}</button>
    <button type="button" data-filter="app" aria-pressed="false">Apps {n_apps}</button>
    <button type="button" data-filter="game" aria-pressed="false">Games {n_games}</button>
  </div>
  <div class="appgrid" id="appgrid" data-filter="all">
{chr(10).join(cards)}
  </div>
</section>

<section class="card">
  <div class="kicker">How we build</div>
  <h2>The same three rules, in every app</h2>
  <div class="grid">
    <div class="feat">
      <span class="num">01</span>
      <b>No accounts</b>
      <p>Nothing we ship asks you to sign up. There is no login, no email capture and no
      profile — so there is no database of users to leak.</p>
    </div>
    <div class="feat">
      <span class="num">02</span>
      <b>No analytics, no ads</b>
      <p>No advertising networks, no analytics SDKs, no crash reporters and no third-party
      trackers are compiled into any of our apps.</p>
    </div>
    <div class="feat">
      <span class="num">03</span>
      <b>On-device by default</b>
      <p>Your data stays where it was created. Several apps ship with no networking
      capability at all, so the operating system itself blocks a connection.</p>
    </div>
  </div>
</section>

<section class="card">
  <div class="kicker">Policies</div>
  <h2>Everything a store review needs, in one place</h2>
  <p>These are the pages linked from our App Store and Google Play listings, and from inside
  the apps themselves.</p>
  <div class="grid">
    <div class="feat"><b>Privacy Policy</b><p>What every app stores, and why nothing reaches
      us. <a class="go" href="/privacy/">Read {ARROW}</a></p></div>
    <div class="feat"><b>Terms of Use</b><p>Licence, refunds, warranty and the store-specific
      terms. <a class="go" href="/terms/">Read {ARROW}</a></p></div>
    <div class="feat"><b>Data &amp; Account Deletion</b><p>How to remove everything an app
      holds. <a class="go" href="/data-deletion/">Read {ARROW}</a></p></div>
    <div class="feat"><b>Children's Privacy</b><p>Our COPPA, Google Play Families and Kids
      Category position. <a class="go" href="/kids/">Read {ARROW}</a></p></div>
    <div class="feat"><b>Accessibility</b><p>What we support today and what we are still
      working on. <a class="go" href="/accessibility/">Read {ARROW}</a></p></div>
    <div class="feat"><b>Security</b><p>How to report a vulnerability, and what to expect
      back. <a class="go" href="/security/">Read {ARROW}</a></p></div>
  </div>
</section>

<section class="card">
  <div class="kicker">Contact</div>
  <h2>Talk to a person</h2>
  <p>Support, privacy questions, bug reports and store-review enquiries all go to the same
  address, and are answered by the developer.</p>
  <p><b>Email:</b> <a href="mailto:{EMAIL}">{EMAIL}</a><br />
  <b>Website:</b> <a href="https://{SITE['domain']}">{SITE['domain']}</a></p>
  <div class="cta">
    <a class="btn primary" href="mailto:{EMAIL}">Email support</a>
    <a class="btn" href="/privacy/">Privacy policies</a>
    <a class="btn" href="/terms/">Terms of use</a>
  </div>
</section>

{HOME_SCRIPT}"""

    return write("index.html", page(
        f"{COMPANY} — apps that keep your data on your device",
        f"{COMPANY} builds focused apps and games for iPhone, iPad, Android and Mac. "
        "No accounts, no analytics, no ads. Support and privacy policies for every app.",
        body,
        canonical="/",
    ))


# --------------------------------------------------------------------------
# Per-app overview
# --------------------------------------------------------------------------

def build_app_page(app):
    feats = "\n".join(
        f'    <div class="feat"><span class="num">{i:02d}</span><b>{e(t)}</b><p>{e(d)}</p></div>'
        for i, (t, d) in enumerate(app["features"], 1)
    )
    longs = "\n  ".join(f"<p>{e(p)}</p>" for p in app["long"])

    rows = [
        ("Category", e(app["category"])),
        ("Platforms", e(", ".join(app["platforms"]))),
        ("Availability", app["status"]),
    ]
    if app["bundle_ids"]:
        rows.append(("Bundle identifier",
                     ", ".join(f"<code>{e(b)}</code>" for b in app["bundle_ids"])))
    rows += [
        ("Account required", "No — there is no sign-up or login"),
        ("Data collected", "None"),
    ]
    # Only stated where it has been verified against the app itself.
    if app["privacy"].get("purchases"):
        rows.append(("In-app purchases", md_inline(app["privacy"]["purchases"])))
    rows += [
        ("Privacy policy",
         f'<a href="/apps/{app["slug"]}/privacy/">{SITE["domain"]}/apps/{app["slug"]}/privacy/</a>'),
        ("Support",
         f'<a href="/apps/{app["slug"]}/support/">{SITE["domain"]}/apps/{app["slug"]}/support/</a>'),
    ]
    spec = "\n".join(
        f"      <tr><th scope=\"row\">{k}</th><td>{v}</td></tr>" for k, v in rows
    )

    body = f"""{back_to_apps()}
{app_header(app)}

<section class="card apphero">
  {app_icon(app, "xl", eager=True)}
  <div>
    <div class="kicker">{e(app['category'])} · {e(' · '.join(app['platforms']))}</div>
    <h1>{e(app['name'])}</h1>
    <p class="lede">{e(app['summary'])}</p>
    <div style="margin-top:18px">{platform_pills(app)} {status_badge(app)}</div>
    <div class="cta">
      <a class="btn primary" href="/apps/{app['slug']}/support/">Support {ARROW}</a>
      <a class="btn" href="/apps/{app['slug']}/privacy/">Privacy policy</a>
      <a class="btn" href="mailto:{EMAIL}?subject={e(app['name'])}">Email us</a>
    </div>
  </div>
</section>

<section class="card">
  <div class="kicker">Overview</div>
  <h2>{e(app['tagline'])}</h2>
  {longs}
</section>

<section class="card">
  <div class="kicker">Features</div>
  <h2>What it does</h2>
  <div class="grid">
{feats}
  </div>
</section>

<div class="grid two">
  <section class="card" style="margin-top:18px">
    <div class="kicker">Privacy at a glance</div>
    <h2>{'This app collects no data' if not app['privacy']['collects_data'] else 'What this app collects'}</h2>
    <p>{md_inline(app['privacy']['headline'])}</p>
    <div class="cta">
      <a class="btn" href="/apps/{app['slug']}/privacy/">Read the full policy {ARROW}</a>
    </div>
  </section>

  <section class="card" style="margin-top:18px">
    <div class="kicker">At a glance</div>
    <h2>Details</h2>
    <div class="tablewrap">
      <table class="spec">
        <tbody>
{spec}
        </tbody>
      </table>
    </div>
  </section>
</div>"""

    return write(f"apps/{app['slug']}/index.html", page(
        f"{app['name']} — {app['tagline']}",
        app["summary"],
        body,
        accent=app["accent"],
        canonical=f"/apps/{app['slug']}/",
    ))


# --------------------------------------------------------------------------
# Per-app privacy policy
# --------------------------------------------------------------------------

def build_app_privacy(app):
    p = app["privacy"]

    stored_rows = "\n".join(
        f"      <tr><td>{e(w)}</td><td>{e(where)}</td><td>{e(why)}</td></tr>"
        for w, where, why in p["stored"]
    )
    perms = "\n".join(
        f"    <li><b>{e(name)}</b> — {md_inline(desc)}</li>"
        for name, desc in p["permissions"]
    )

    sections = []

    sections.append(f"""<h2 id="collect">1. What we collect</h2>
<p><b>Nothing.</b> There is no sign-up, no login, no email address collected, no advertising
identifier, no usage analytics and no crash reporting. No SDK in the app reports your
behaviour to anyone.</p>
<p>{e(COMPANY)} operates no server that holds your {e(app['name'])} data, because no such data
ever reaches us. That is not a policy decision we could quietly reverse in an update — there is
no backend to send it to.</p>""")

    sections.append(f"""<h2 id="stored">2. What the app stores, and where</h2>
<p>Everything {e(app['name'])} saves is stored on the device you are using it on.</p>
<div class="tablewrap">
  <table>
    <thead><tr><th>What</th><th>Where</th><th>Why</th></tr></thead>
    <tbody>
{stored_rows}
    </tbody>
  </table>
</div>""")

    sections.append(f"""<h2 id="permissions">3. Permissions</h2>
<p>{e(app['name'])} asks for the following, and nothing else. Every permission marked
optional can be declined, and the app keeps working without it.</p>
<ul>
{perms}
</ul>""")

    sections.append(f"""<h2 id="network">4. Network activity</h2>
<p>{md_inline(p['network'])}</p>""")

    sections.append(f"""<h2 id="third-parties">5. Third parties</h2>
<p>{md_inline(p['third_parties'])}</p>
<p>We do not sell, rent, share or disclose your personal information, because we do not
hold any of it.</p>""")


    store_note = ""
    if p.get("store_note"):
        store_note = f"""<p>{md_inline(p['store_note'])}</p>"""
    # Only declare against stores the app actually ships on. A macOS-only
    # title carrying a "Google Play — Data safety" row reads as boilerplate
    # and invites the reviewer to wonder what else was pasted in unchecked.
    on_apple = any(pl in ("iOS", "iPadOS", "macOS") for pl in app["platforms"])
    on_google = "Android" in app["platforms"]
    store_rows = ""
    if on_apple:
        store_rows += """
      <tr><td>Apple App Store — App Privacy</td>
          <td>Data Not Collected. Nothing is collected from this app, by us or by anyone else,
          so no data type is linked to you and none is used to track you.</td></tr>"""
    if on_google:
        store_rows += """
      <tr><td>Google Play — Data safety</td>
          <td>No data collected. No data shared with third parties. No data is transmitted off
          the device, so there is none to encrypt in transit. Users can erase everything the
          app holds by deleting it.</td></tr>"""
    if on_apple and on_google:
        store_intro = "Apple and Google each require a privacy declaration alongside the app listing."
    elif on_google:
        store_intro = "Google requires a privacy declaration alongside the app listing."
    else:
        store_intro = "Apple requires a privacy declaration alongside the app listing."

    sections.append(f"""<h2 id="store-labels">6. What we declare to the app stores</h2>
<p>{store_intro} These are the
answers we give for {e(app['name'])}, reproduced here so you can check them against the rest of
this policy.</p>
<div class="tablewrap">
  <table>
    <thead><tr><th>Store declaration</th><th>Our answer</th></tr></thead>
    <tbody>{store_rows}
      <tr><td>Account deletion</td>
          <td>Not applicable — the app has no account. See
          <a href="/data-deletion/">Data &amp; Account Deletion</a>.</td></tr>
    </tbody>
  </table>
</div>
{store_note}""")

    n = 7
    if p.get("purchases"):
        sections.append(f"""<h2 id="purchases">{n}. Purchases</h2>
<p>{md_inline(p['purchases'])}</p>""")
        n += 1

    children_text = p.get("children") or (
        f"{app['name']} is not directed at children under 13, and it collects no personal "
        "information from anyone of any age. Because nothing is collected, nothing is "
        "collected from children."
    )
    sections.append(f"""<h2 id="children">{n}. Children</h2>
<p>{md_inline(children_text)}</p>""")
    n += 1

    if p.get("health_note"):
        sections.append(f"""<h2 id="health">{n}. Health data</h2>
<p>{md_inline(p['health_note'])}</p>
<p>Health information is never used for advertising, marketing, or any purpose other than
displaying it to you inside the app, and it is never shared with a third party or with us.</p>""")
        n += 1

    if p.get("extra"):
        sections.append(f"""<h2 id="notes">{n}. Additional notes</h2>
<p>{md_inline(p['extra'])}</p>""")
        n += 1

    sections.append(f"""<h2 id="rights">{n}. Your rights and your choices</h2>
<p>Privacy laws including the GDPR and the CCPA give you rights to access, correct, export
and delete personal data a company holds about you. {e(COMPANY)} holds no personal data
about {e(app['name'])} users, so there is nothing for us to produce, correct or erase on
request.</p>
<p>You remain in full control of the data on your own device:</p>
<ul>
  <li>Delete individual items from inside the app.</li>
  <li>Remove the app to delete its local data, subject to your device's own backup and
  restore settings.</li>
  <li>Revoke any permission at any time from your device's system settings.</li>
</ul>
<p>We do not sell personal information and never have. We do not share personal information
for cross-context behavioural advertising.</p>""")
    n += 1

    sections.append(f"""<h2 id="security">{n}. Security</h2>
<p>Because your data stays on your device, its security rests on your device's own
protections — your passcode, your biometric lock and your operating system's storage
encryption. Keep your device updated and locked.</p>""")
    n += 1

    sections.append(f"""<h2 id="changes">{n}. Changes to this policy</h2>
<p>If this policy changes, the revised version will be published at this address with a new
date at the top. If a future version of {e(app['name'])} ever begins collecting data, this
policy will be updated <em>before</em> that version is released, and the app will ask for
your consent in-app.</p>""")
    n += 1

    sections.append(f"""<h2 id="contact">{n}. Contact</h2>
<p>Questions about this policy, or about privacy in any {e(COMPANY)} app:</p>
<ul>
  <li>Email: <a href="mailto:{EMAIL}">{EMAIL}</a></li>
  <li>Support: <a href="/apps/{app['slug']}/support/">{SITE['domain']}/apps/{app['slug']}/support/</a></li>
</ul>
<p>We aim to answer within a few business days.</p>""")

    toc_items = [
        ("collect", "What we collect"), ("stored", "What is stored"),
        ("permissions", "Permissions"), ("network", "Network"),
        ("third-parties", "Third parties"), ("store-labels", "Store declarations"),
        ("children", "Children"),
        ("rights", "Your rights"), ("contact", "Contact"),
    ]
    toc = "\n".join(f'    <a href="#{i}">{e(t)}</a>' for i, t in toc_items)

    body = f"""{app_header(app, 'Privacy Policy')}

<section class="card legal">
  <div class="kicker">{e(app['name'])}</div>
  <h1>Privacy Policy</h1>
  <p class="meta-line">Last updated: {e(UPDATED)} · Applies to {e(app['name'])} for
  {e(', '.join(app['platforms']))}, all versions</p>

  <div class="note">
    <p><b>The short version.</b> {md_inline(p['headline'])}</p>
  </div>

  <div class="toc">
{toc}
  </div>

  <p style="margin-top:22px">This Privacy Policy explains how {e(COMPANY)} (&ldquo;we&rdquo;,
  &ldquo;us&rdquo;) handles information in {e(app['name'])} (the &ldquo;app&rdquo;). It is
  written to be read, not to be survived.</p>

{chr(10).join(chr(10) + s for s in sections)}
</section>"""

    return write(f"apps/{app['slug']}/privacy/index.html", page(
        f"Privacy Policy — {app['name']}",
        f"Privacy policy for {app['name']} by {COMPANY}. {p['headline']}",
        body,
        accent=app["accent"],
    ))


# --------------------------------------------------------------------------
# Per-app support page
# --------------------------------------------------------------------------

def build_app_support(app):
    s = app["support"]
    faqs = "\n".join(
        f"  <details><summary>{e(q)}</summary><p>{md_inline(a)}</p></details>"
        for q, a in s["faq"]
    )
    report = "\n".join(f"      <li>{e(r)}</li>" for r in s["report"])

    body = f"""{app_header(app, 'Support')}

<section class="card">
  <div class="kicker">{e(app['category'])} · {e(' · '.join(app['platforms']))}</div>
  <h1>{e(app['name'])} Support</h1>
  <p class="lede">{e(app['summary'])}</p>
  <div style="margin-top:16px">{platform_pills(app)} {status_badge(app)}</div>
</section>

<div class="grid two">
  <section class="card" style="margin-top:16px">
    <h2>Contact us</h2>
    <p>Email the developer directly. There is no ticket system and no bot in between.</p>
    <ul>
      <li>Email: <a href="mailto:{EMAIL}?subject={e(app['name'])}%20support">{EMAIL}</a></li>
      <li>Website: <a href="https://{SITE['domain']}">{SITE['domain']}</a></li>
      <li>Privacy policy: <a href="/apps/{app['slug']}/privacy/">{e(app['name'])} privacy policy</a></li>
    </ul>
    <p style="margin-top:12px">We aim to reply within a few business days.</p>
  </section>

  <section class="card" style="margin-top:16px">
    <h2>Reporting a problem</h2>
    <p>Please include as much of this as you can — it usually turns a week of guessing into
    a same-day fix:</p>
    <ul>
{report}
    </ul>
  </section>
</div>

<section class="card">
  <div class="kicker">FAQ</div>
  <h2>Common questions</h2>
{faqs}
</section>

<section class="card">
  <div class="kicker">Your data</div>
  <h2>Privacy and data requests</h2>
  <p>{md_inline(app['privacy']['headline'])}</p>
  <p>Because nothing leaves your device, there is no account to close and no server-side
  data for us to export or delete. To remove everything the app has stored, delete the app
  from your device. Full detail is in the
  <a href="/apps/{app['slug']}/privacy/">{e(app['name'])} privacy policy</a>.</p>
</section>"""

    return write(f"apps/{app['slug']}/support/index.html", page(
        f"Support — {app['name']}",
        f"Support and contact for {app['name']} by {COMPANY}. "
        f"Email {EMAIL} for help, bug reports and privacy questions.",
        body,
        accent=app["accent"],
    ))


# --------------------------------------------------------------------------
# Site-wide privacy hub
# --------------------------------------------------------------------------

def build_privacy_hub():
    rows = "\n".join(
        f"""      <tr>
        <td><a href="/apps/{a['slug']}/privacy/">{e(a['name'])}</a></td>
        <td>{e(', '.join(a['platforms']))}</td>
        <td>No</td>
        <td>{e(a['status'])}</td>
      </tr>"""
        for a in APPS
    )
    links = "\n".join(
        f'    <a href="/apps/{a["slug"]}/privacy/">{e(a["name"])}</a>' for a in APPS
    )

    body = f"""<section class="card legal">
  <div class="kicker">{e(COMPANY)}</div>
  <h1>Privacy Policy</h1>
  <p class="meta-line">Last updated: {e(UPDATED)} · Applies to every {e(COMPANY)} app</p>

  <div class="note">
    <p><b>The short version.</b> No {e(COMPANY)} app collects personal information. There
    are no accounts, no analytics, no advertising and no trackers in anything we ship. Your
    data stays on your device.</p>
  </div>

  <p style="margin-top:22px">This is the policy that covers all of our apps. Each app also
  has its own policy that describes exactly what that app stores and which permissions it
  asks for — those are the URLs listed on the App Store and Google Play, and they are linked
  below. Where an app-specific policy and this one differ in detail, the app-specific
  policy governs that app.</p>

  <div class="toc">
{links}
  </div>

<h2 id="who">1. Who we are</h2>
<p>{e(COMPANY)} is an independent app developer. We publish the apps listed on this site to
the Apple App Store and Google Play. You can reach a person at
<a href="mailto:{EMAIL}">{EMAIL}</a>.</p>

<h2 id="collect">2. What we collect</h2>
<p><b>Nothing.</b> None of our apps collects personal information, and we operate no server
that stores user data. Specifically, across every app we publish:</p>
<ul>
  <li>No account, sign-up, login or email capture.</li>
  <li>No analytics or telemetry SDK of any kind.</li>
  <li>No advertising, advertising identifiers or advertising SDKs.</li>
  <li>No crash or diagnostic reporting sent to us.</li>
  <li>No location tracking, contact-list access or device fingerprinting.</li>
  <li>No third-party trackers compiled into any build.</li>
</ul>

<h2 id="summary">3. Per-app summary</h2>
<div class="tablewrap">
  <table>
    <thead><tr><th>App</th><th>Platforms</th><th>Collects personal data</th><th>Status</th></tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>
</div>

<h2 id="device">4. Data on your device</h2>
<p>Our apps do store things — a fasting history, a screenshot library, an encrypted vault, a
saved game. All of it is written to your device's own storage, and none of it is transmitted
to us. Each app's own policy lists exactly what it keeps and where.</p>

<h2 id="network">5. Network connections</h2>
<p>Most of our apps make no network connections at all; several ship without any networking
capability, so the operating system itself prevents a connection. Where an app does reach
the network, it is for a feature you asked for, it is described plainly in that app's policy,
and it never carries your personal data. The two current cases are Keybound's opt-in breach
check, which sends a five-character hash prefix and nothing more, and Universal Remote, which
talks to a television on your own local network.</p>

<h2 id="support">6. Support communications</h2>
<p>If you email us for support, we receive what you choose to put in that email — your
address, your message and any screenshot or log you attach. We use it only to answer you, we
do not add you to a mailing list, and we do not share it. Please do not send us passwords,
recovery keys or the contents of an encrypted vault; we never need them.</p>

<h2 id="sharing">7. Sharing and selling</h2>
<p>We do not sell, rent, share or disclose personal information. We hold none to sell. We do
not share personal information for cross-context behavioural advertising, and we have never
done so.</p>

<h2 id="children">8. Children</h2>
<p>Several of our games are suitable for children. Because none of our apps collects any data
from anyone, none of them collects data from children — there is nothing to disclose, share or
delete. Our games contain no advertising, no in-app purchases, no chat and no user-generated
content. We comply with COPPA, the Google Play Families policy and the App Store Kids Category
requirements by not collecting anything in the first place.</p>

<h2 id="rights">9. Your rights</h2>
<p>Under the GDPR, the UK GDPR, the CCPA/CPRA and comparable laws, you have the right to
access, correct, port and delete personal data a company holds about you, and to object to
its processing. We hold no personal data about our users, so there is nothing for us to
produce, correct, port or erase.</p>
<p>You control the data on your own device: delete items inside an app, revoke a permission
in system settings, or remove the app to clear its local data. You will never be discriminated
against for exercising a privacy right.</p>

<h2 id="transfers">10. International transfers</h2>
<p>Since no personal data is collected, no personal data is transferred internationally or
stored in any jurisdiction.</p>

<h2 id="retention">11. Retention</h2>
<p>We retain no user data, so there is no retention period to state. Data you create inside an
app stays on your device for as long as you keep it there. Support emails are kept only as long
as needed to resolve your question.</p>

<h2 id="changes">12. Changes to this policy</h2>
<p>If this policy changes, the revised version will appear at this address with a new date at
the top. If any app ever begins collecting data, the relevant policy will be updated
<em>before</em> that version ships, and the app will ask for your consent in-app.</p>

<h2 id="website">13. This website</h2>
<p>flowlabapps.com is a set of static HTML pages. It sets no cookies, runs no analytics, embeds
no tracking pixel, loads no third-party font, script or advertising tag, and has no comment
system, contact form or login. Nothing on the site attempts to identify you or follow you
between pages, and there is no cookie banner because there is nothing to consent to.</p>
<p>The site is hosted on Cloudflare Pages. Like any web host, Cloudflare processes the requests
your browser makes in order to deliver the page and to protect the site from abuse, which
involves your IP address and standard request metadata. That processing is governed by
<a href="https://www.cloudflare.com/privacypolicy/">Cloudflare's privacy policy</a>. We do not
receive, request or retain those logs, and we have no visitor analytics dashboard of any kind.
Links out to Apple, Google or other third-party sites are governed by those sites' own
policies once you follow them.</p>

<h2 id="more">14. Related policies</h2>
<ul>
  <li><a href="/data-deletion/">Data &amp; Account Deletion</a> — how to erase everything an
  app holds, and how to ask us in writing.</li>
  <li><a href="/kids/">Children's Privacy</a> — our COPPA, Google Play Families and App Store
  Kids Category position.</li>
  <li><a href="/security/">Security</a> — how to report a vulnerability.</li>
  <li><a href="/terms/">Terms of Use</a> — licence, refunds and warranty.</li>
</ul>

<h2 id="contact">15. Contact</h2>
<p>Privacy questions, data requests and store-review enquiries:</p>
<ul>
  <li>Email: <a href="mailto:{EMAIL}">{EMAIL}</a></li>
  <li>Support: <a href="/support/">{SITE['domain']}/support/</a></li>
</ul>
<p>We aim to answer within a few business days.</p>
</section>"""

    return write("privacy/index.html", page(
        f"Privacy Policy — {COMPANY}",
        f"Privacy policy for all {COMPANY} apps. No accounts, no analytics, no advertising. "
        "Your data stays on your device. Per-app policies linked.",
        body,
    ))


# --------------------------------------------------------------------------
# Site-wide support hub
# --------------------------------------------------------------------------

def build_support_hub():
    rows = "\n".join(
        f"""      <tr>
        <td>{e(a['name'])}</td>
        <td>{e(', '.join(a['platforms']))}</td>
        <td><a href="/apps/{a['slug']}/support/">Support</a> ·
            <a href="/apps/{a['slug']}/privacy/">Privacy</a></td>
      </tr>"""
        for a in APPS
    )

    body = f"""<section class="card">
  <div class="kicker">{e(COMPANY)}</div>
  <h1>Support</h1>
  <p class="lede">One address, answered by the developer who wrote the app. No ticket
  numbers, no chatbot, no support tier.</p>
  <div class="cta">
    <a class="btn primary" href="mailto:{EMAIL}">{EMAIL}</a>
    <a class="btn" href="/privacy/">Privacy policies</a>
  </div>
</section>

<section class="card">
  <div class="kicker">Per-app support</div>
  <h2>Pick your app</h2>
  <p>Each app has its own support page with questions specific to it, and its own privacy
  policy. These are the URLs published on the App Store and Google Play.</p>
  <div class="tablewrap">
    <table>
      <thead><tr><th>App</th><th>Platforms</th><th>Pages</th></tr></thead>
      <tbody>
{rows}
      </tbody>
    </table>
  </div>
</section>

<div class="grid two">
  <section class="card" style="margin-top:16px">
    <h2>Reporting a bug</h2>
    <p>Include as much of this as you can:</p>
    <ul>
      <li>Which app, and its version number</li>
      <li>Device model and OS version</li>
      <li>What you expected versus what actually happened</li>
      <li>Steps to reproduce it</li>
      <li>Roughly when it happened</li>
      <li>A screenshot, if the problem is visible</li>
    </ul>
    <p style="margin-top:12px">Never send us a password, a recovery key or the contents of an
    encrypted vault. We never need them, and we cannot help more with them.</p>
  </section>

  <section class="card" style="margin-top:16px">
    <h2>Privacy and data requests</h2>
    <p>None of our apps collects personal data, and we run no servers holding user
    information. There is no account to close and nothing on our side to export or delete.</p>
    <p>To remove what an app has stored locally, delete the app from your device. To withdraw
    a permission, use your device's system settings.</p>
    <p>Step-by-step instructions are on the
    <a href="/data-deletion/">Data &amp; Account Deletion</a> page. If you would like it
    confirmed in writing for a compliance process, email us and we will respond.</p>
  </section>
</div>

<section class="card">
  <div class="kicker">Policies</div>
  <h2>Everything else you might be looking for</h2>
  <div class="grid">
    <div class="feat"><b>Privacy Policy</b><p>What every app stores, and why nothing reaches us.
      <a href="/privacy/">Read</a></p></div>
    <div class="feat"><b>Terms of Use</b><p>Licence, refunds, warranty and store-specific terms.
      <a href="/terms/">Read</a></p></div>
    <div class="feat"><b>Data &amp; Account Deletion</b><p>How to erase everything an app holds.
      <a href="/data-deletion/">Read</a></p></div>
    <div class="feat"><b>Children's Privacy</b><p>COPPA, Google Play Families and the Kids
      Category. <a href="/kids/">Read</a></p></div>
    <div class="feat"><b>Accessibility</b><p>What we support, and what we are still working on.
      <a href="/accessibility/">Read</a></p></div>
    <div class="feat"><b>Security</b><p>How to report a vulnerability. <a href="/security/">Read</a></p></div>
  </div>
</section>

<section class="card">
  <div class="kicker">Common questions</div>
  <h2>Across all our apps</h2>
  <details><summary>Do I need an account for any of your apps?</summary>
    <p>No. Not one of them has a sign-up, a login or an account system.</p></details>
  <details><summary>Do your apps work offline?</summary>
    <p>Almost entirely. Several ship without any networking capability at all. The exceptions
    are Keybound's opt-in breach check and Universal Remote, which talks to a TV on your own
    local network.</p></details>
  <details><summary>Do you show ads or track me?</summary>
    <p>No. There are no advertising networks, analytics SDKs, crash reporters or third-party
    trackers in anything we publish.</p></details>
  <details><summary>How do I request a refund?</summary>
    <p>Purchases are handled entirely by Apple and Google, so refunds go through them. On iOS
    and macOS use <a href="https://reportaproblem.apple.com">reportaproblem.apple.com</a>; on
    Android use the Google Play order history. We cannot issue a refund ourselves.</p></details>
  <details><summary>How do I delete my data?</summary>
    <p>Delete the app. Its local data goes with it, subject to your device's backup and restore
    settings. There is nothing on our side to delete.</p></details>
  <details><summary>Can I use an app on more than one device?</summary>
    <p>Yes, within the terms of your App Store or Google Play purchase. Note that most of our
    apps do not sync, so data created on one device stays on that device.</p></details>
</section>"""

    return write("support/index.html", page(
        f"Support — {COMPANY}",
        f"Support and contact for all {COMPANY} apps. Email {EMAIL} for help, bug reports, "
        "refunds and privacy questions.",
        body,
    ))




# --------------------------------------------------------------------------
# Data and account deletion
#
# Google Play's Data safety form asks for a deletion URL, and App Review
# guideline 5.1.1(v) asks how a user removes what an app holds. Neither is
# satisfied by "we collect nothing" alone — a reviewer wants a page.
# --------------------------------------------------------------------------

def build_data_deletion():
    rows = "\n".join(
        f"""      <tr>
        <td><a href="/apps/{a['slug']}/">{e(a['name'])}</a></td>
        <td>{e(', '.join(a['platforms']))}</td>
        <td>No account exists</td>
        <td>Delete the app</td>
      </tr>"""
        for a in APPS
    )

    body = f"""<section class="card legal">
  <div class="kicker">{e(COMPANY)}</div>
  <h1>Data &amp; Account Deletion</h1>
  <p class="meta-line">Last updated: {e(UPDATED)} · Applies to every {e(COMPANY)} app</p>

  <div class="note">
    <p><b>The short version.</b> None of our apps has an account, and we hold no user data on
    any server. Deleting the app deletes everything it stored. If you want that confirmed in
    writing, email <a href="mailto:{EMAIL}">{EMAIL}</a> and we will reply.</p>
  </div>

  <div class="toc">
    <a href="#accounts">Accounts</a>
    <a href="#how">How to delete</a>
    <a href="#apps">Per app</a>
    <a href="#backups">Backups</a>
    <a href="#request">Written confirmation</a>
  </div>

<h2 id="accounts">1. There is no account to delete</h2>
<p>No {e(COMPANY)} app has a sign-up, a login, a profile or a user identifier. We operate no
server that stores user data, so there is no account record, no cloud copy and no server-side
backup of anything you have created. This is why we cannot offer an in-app &ldquo;delete my
account&rdquo; button: there is no account for it to delete.</p>
<p>If you have emailed us for support, we hold that email thread and nothing else. You can ask
us to delete it at any time — see section 5.</p>

<h2 id="how">2. How to delete what an app has stored</h2>
<p>Everything our apps save is written to your own device. Removing the app removes it.</p>

<h3>iPhone and iPad</h3>
<ul>
  <li>Touch and hold the app icon, choose <b>Remove App</b>, then <b>Delete App</b>; or</li>
  <li>Open <b>Settings → General → iPhone Storage</b>, select the app and choose
  <b>Delete App</b>. Note that <b>Offload App</b> deliberately keeps its data — use Delete.</li>
</ul>

<h3>Mac</h3>
<ul>
  <li>Move the app from your <b>Applications</b> folder to the Trash and empty it.</li>
  <li>Sandboxed app data lives in <code>~/Library/Containers/</code> and preferences in
  <code>~/Library/Preferences/</code>. Removing the app's container folder there clears
  anything left behind.</li>
</ul>

<h3>Android</h3>
<ul>
  <li>Open <b>Settings → Apps</b>, select the app, then <b>Storage &amp; cache → Clear
  storage</b> to erase its data while keeping the app; or</li>
  <li>Choose <b>Uninstall</b> to remove the app and its data together.</li>
</ul>

<h3>Inside an app</h3>
<p>Most of our apps also let you delete individual items without removing the app — a fasting
session, a screenshot, a vault entry, a saved game. Where an app stores documents you chose
yourself, those files are yours and stay where you put them.</p>

<h2 id="apps">3. Per-app summary</h2>
<div class="tablewrap">
  <table>
    <thead><tr><th>App</th><th>Platforms</th><th>Server-side data</th><th>To erase everything</th></tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>
</div>
<p style="margin-top:14px">Each app's own privacy policy lists exactly what it writes to your
device and where.</p>

<h2 id="backups">4. One thing deleting the app does not reach</h2>
<p>If your device backs itself up — iCloud Backup, Finder or iTunes backup, or Google One
backup on Android — a copy of an app's data may exist inside a backup you made before deleting
it. That backup belongs to you and sits in your Apple or Google account, not ours. To remove
it, manage or delete the backup in your device's own settings. We have no access to it and no
way to reach it.</p>

<h2 id="request">5. Asking us in writing</h2>
<p>Some employers, schools and compliance processes want a written statement rather than a
policy page. Email <a href="mailto:{EMAIL}">{EMAIL}</a> with the app name and we will confirm,
in writing, that we hold no personal data about you and that nothing needs to be erased on our
side.</p>
<p>To have a support email thread deleted, say so in your message. We will remove it and
confirm. We do not need to verify your identity first, because the thread is the only thing we
hold and you are already the person we are replying to.</p>
</section>"""

    return write("data-deletion/index.html", page(
        f"Data & Account Deletion — {COMPANY}",
        f"How to delete data held by {COMPANY} apps. No app has an account and no data is "
        "held on our servers; deleting the app erases everything it stored.",
        body,
        canonical="/data-deletion/",
    ))


# --------------------------------------------------------------------------
# Children's privacy
#
# Required in substance by COPPA, the Google Play Families policy and the App
# Store Kids Category rules, all of which want the position stated explicitly
# rather than inferred from a general policy.
# --------------------------------------------------------------------------

def build_kids():
    games = [a for a in APPS if is_game(a)]
    game_rows = "\n".join(
        f"""      <tr>
        <td><a href="/apps/{a['slug']}/">{e(a['name'])}</a></td>
        <td>{e(', '.join(a['platforms']))}</td>
        <td>None</td>
        <td>No</td>
        <td>{'None' if a['privacy'].get('purchases') else '&mdash;'}</td>
      </tr>"""
        for a in games
    )

    body = f"""<section class="card legal">
  <div class="kicker">{e(COMPANY)}</div>
  <h1>Children's Privacy</h1>
  <p class="meta-line">Last updated: {e(UPDATED)} · COPPA, Google Play Families and
  App Store Kids Category</p>

  <div class="note">
    <p><b>The short version.</b> Our apps collect nothing from anyone, at any age. There is no
    advertising, no analytics, no chat, no user-generated content and no third-party SDK in
    any of them — so there is nothing about a child to collect, share, sell or delete.</p>
  </div>

  <div class="toc">
    <a href="#position">Our position</a>
    <a href="#games">Our games</a>
    <a href="#coppa">COPPA</a>
    <a href="#families">Google Play Families</a>
    <a href="#apple">Apple Kids Category</a>
    <a href="#parents">For parents</a>
  </div>

<h2 id="position">1. Our position</h2>
<p>We do not knowingly collect personal information from children under 13 — or from anyone
else. That is not a promise about how we handle children's data specially; it is a consequence
of how the apps are built. There is no account system, no analytics SDK, no advertising
network, no crash reporter and no third-party library that could report a child's behaviour to
anyone, because none of those things are compiled into the builds.</p>
<p>Since we collect nothing, we do not need — and never ask for — verifiable parental consent,
because there is no collection to consent to.</p>

<h2 id="games">2. Our games</h2>
<p>The following titles are suitable for a broad audience including children:</p>
<div class="tablewrap">
  <table>
    <thead><tr><th>Game</th><th>Platforms</th><th>Data collected</th><th>Ads</th><th>In-app purchases</th></tr></thead>
    <tbody>
{game_rows}
    </tbody>
  </table>
</div>
<p style="margin-top:14px">None of them contains chat, messaging, friend lists, user-generated
content shared between players, social network integration, or a link out to an external
website or store from inside gameplay.</p>

<h2 id="coppa">3. COPPA</h2>
<p>The Children's Online Privacy Protection Act applies to the online collection of personal
information from children under 13. Our apps perform no such collection: no persistent
identifier is created or transmitted, no advertising identifier is read, no location is
recorded, and no contact information is requested. Because nothing is collected, there is
nothing to disclose to a parent, nothing to share with a third party, and nothing for a parent
to request the deletion of.</p>
<p>If you believe a child has somehow provided us with personal information — for example by
emailing us directly — contact <a href="mailto:{EMAIL}">{EMAIL}</a> and we will delete that
message.</p>

<h2 id="families">4. Google Play Families policy</h2>
<p>For titles distributed to a child or mixed audience on Google Play, we confirm that they:</p>
<ul>
  <li>Contain no ads of any kind, and therefore no ad SDK subject to the families
  self-certified ads programme.</li>
  <li>Collect and transmit no personal or sensitive user data, and use no Android advertising
  identifier or other persistent identifier.</li>
  <li>Include no third-party SDK that is not approved for a child audience — there are no
  third-party SDKs at all.</li>
  <li>Contain no in-app purchases, no loot boxes and no simulated gambling.</li>
  <li>Contain no social features, chat or user-generated content.</li>
  <li>Are rated through the official IARC questionnaire, answered honestly.</li>
</ul>

<h2 id="apple">5. Apple App Store Kids Category</h2>
<p>Where a title is submitted to the Kids Category, it complies with App Review guideline 1.3
and section 5.1.4: it includes no third-party analytics or advertising, transmits no personally
identifiable information or device information to third parties, contains no links out of the
app, no purchasing opportunities and no other distractions to a child, other than behind a
parental gate where one is genuinely required. Because the apps have no network capability for
these purposes, the requirement is met by construction rather than by configuration.</p>

<h2 id="parents">6. For parents</h2>
<p>Everything a child creates in one of our games — progress, unlocks, settings — stays on the
device it was created on. To remove it, delete the app; see
<a href="/data-deletion/">Data &amp; Account Deletion</a>. To restrict purchases or downloads
generally, use Screen Time on iOS and iPadOS, or Google Family Link and Play Store parental
controls on Android.</p>
<p>If you have a question about a specific title, email <a href="mailto:{EMAIL}">{EMAIL}</a>.
A person answers.</p>
</section>"""

    return write("kids/index.html", page(
        f"Children's Privacy — {COMPANY}",
        f"{COMPANY}'s children's privacy statement covering COPPA, the Google Play Families "
        "policy and the App Store Kids Category. No data is collected from anyone, at any age.",
        body,
        canonical="/kids/",
    ))


# --------------------------------------------------------------------------
# Accessibility
# --------------------------------------------------------------------------

def build_accessibility():
    body = f"""<section class="card legal">
  <div class="kicker">{e(COMPANY)}</div>
  <h1>Accessibility</h1>
  <p class="meta-line">Last updated: {e(UPDATED)} · This website and our apps</p>

  <div class="note">
    <p><b>The short version.</b> We aim at WCAG 2.2 Level AA for this website and at the
    platform accessibility features on each device for our apps. We are not claiming a
    completed audit — where something falls short, we would like to hear about it and fix it.</p>
  </div>

  <div class="toc">
    <a href="#site">This website</a>
    <a href="#apps">Our apps</a>
    <a href="#known">Known gaps</a>
    <a href="#feedback">Feedback</a>
  </div>

<h2 id="site">1. This website</h2>
<p>The site is plain HTML and CSS with no framework, which makes most of this straightforward:</p>
<ul>
  <li>Semantic landmarks, one <code>h1</code> per page and a heading order that does not skip
  levels.</li>
  <li>A <b>Skip to content</b> link as the first focusable element on every page.</li>
  <li>Visible focus outlines on every interactive element, never removed.</li>
  <li>Body text and interface text meet the 4.5:1 contrast minimum against their background;
  large headings meet 3:1.</li>
  <li>Text is set in relative units and reflows without loss of content down to a 320&nbsp;pixel
  viewport and up to 200% zoom.</li>
  <li>Every control is reachable and operable by keyboard alone. The one piece of scripting on
  the site — the app-type filter on the home page — is a set of real buttons with
  <code>aria-pressed</code> state, and every app remains visible if scripting is unavailable.</li>
  <li><code>prefers-reduced-motion</code> is honoured: all transitions and hover movement are
  disabled when you have asked your system for reduced motion.</li>
  <li>Decorative icons are marked <code>aria-hidden</code> so a screen reader announces the app
  name rather than describing a shape.</li>
</ul>

<h2 id="apps">2. Our apps</h2>
<p>Our apps are built with the native interface toolkit on each platform — SwiftUI and AppKit on
Apple platforms — which means system accessibility features apply rather than being
re-implemented badly: VoiceOver and TalkBack, Dynamic Type and font scaling, Increase Contrast,
Reduce Motion, and full keyboard control on Mac.</p>
<p>Black Hole Rush additionally ships its own in-game accessibility settings: reduced motion,
high contrast, adjustable text size, handedness, camera-shake control, and separate music,
effects and haptics levels. Where a game is built in a cross-platform engine rather than a
native toolkit, we treat that as a reason to provide these controls ourselves.</p>

<h2 id="known">3. Known gaps</h2>
<p>Stating this honestly is more useful than a blanket conformance claim:</p>
<ul>
  <li>We have not commissioned an independent accessibility audit of the website or of any app.</li>
  <li>Our games are visual and time-pressured by design. Colour is not the only signal used to
  convey state, but a fast arcade game will not suit everyone, and no amount of settings
  changes that.</li>
  <li>Screen-reader support in the games is limited to menus and results screens rather than
  live gameplay.</li>
</ul>

<h2 id="feedback">4. Feedback</h2>
<p>If any part of this site or of an app is difficult or impossible for you to use, tell us at
<a href="mailto:{EMAIL}">{EMAIL}</a>. Please include the page or the app, your device and
operating system, and any assistive technology you use. We aim to reply within a few business
days, and accessibility fixes go to the front of the queue.</p>
</section>"""

    return write("accessibility/index.html", page(
        f"Accessibility — {COMPANY}",
        f"Accessibility statement for the {COMPANY} website and apps: WCAG 2.2 AA as the "
        "target, platform accessibility features in the apps, and how to report a barrier.",
        body,
        canonical="/accessibility/",
    ))


# --------------------------------------------------------------------------
# Security and vulnerability disclosure
# --------------------------------------------------------------------------

def build_security():
    body = f"""<section class="card legal">
  <div class="kicker">{e(COMPANY)}</div>
  <h1>Security</h1>
  <p class="meta-line">Last updated: {e(UPDATED)} · Vulnerability disclosure policy</p>

  <div class="note">
    <p><b>Reporting a vulnerability.</b> Email <a href="mailto:{EMAIL}">{EMAIL}</a> with
    &ldquo;Security&rdquo; in the subject. We aim to acknowledge within three business days.
    Please give us a reasonable chance to fix an issue before publishing it.</p>
  </div>

  <div class="toc">
    <a href="#model">Our security model</a>
    <a href="#report">How to report</a>
    <a href="#scope">Scope</a>
    <a href="#safe-harbour">Safe harbour</a>
    <a href="#bounty">Rewards</a>
  </div>

<h2 id="model">1. Our security model</h2>
<p>We run no servers holding user data, so the usual breach story — an exposed database, a
leaked credential dump — does not apply to us. There is no user database anywhere. What matters
instead is the security of the code on your own device, and of the small number of places where
an app touches a network at all.</p>
<ul>
  <li>Keybound derives its key with Argon2id and encrypts its vault with XChaCha20-Poly1305,
  with all cryptography implemented in Rust and the master key never handed to the interface
  layer.</li>
  <li>Keyclave encrypts each document under its own key, wrapped by a master key derived from
  your password, with key material held in the device Keychain marked <em>when unlocked, this
  device only</em>.</li>
  <li>Neither master password can be recovered by us. That is deliberate, and it is what makes
  the encryption meaningful rather than decorative.</li>
  <li>Several apps ship without any networking entitlement, so the operating system blocks a
  connection whether or not the code attempts one.</li>
</ul>

<h2 id="report">2. How to report</h2>
<p>Email <a href="mailto:{EMAIL}">{EMAIL}</a>. A useful report usually includes:</p>
<ul>
  <li>Which app or which page, and the version or the date you tested.</li>
  <li>The device and operating system version.</li>
  <li>What the issue allows an attacker to do, and what access they need first.</li>
  <li>Steps to reproduce, and a proof of concept if you have one.</li>
</ul>
<p>Please do not include real personal data, a real password, a recovery key or the contents of
a real vault in your report. Use test data.</p>
<p>We aim to acknowledge within three business days, to tell you our assessment within ten, and
to keep you updated until it is resolved. If you would like credit in the release notes, say so
and we will include the name or handle you prefer.</p>

<h2 id="scope">3. Scope</h2>
<p><b>In scope:</b> the {e(COMPANY)} apps listed on this site, and this website.</p>
<p><b>Out of scope:</b> denial of service and volumetric testing; social engineering of us or
of our users; physical attacks; spam and mail-configuration reports without a demonstrated
impact; findings that require a jailbroken, rooted or already-compromised device; automated
scanner output with no demonstrated exploit; and issues in Apple's, Google's or Cloudflare's
own infrastructure, which should go to them.</p>

<h2 id="safe-harbour">4. Safe harbour</h2>
<p>If you research in good faith under this policy, we will not pursue or support legal action
against you. Good faith means: you avoid privacy violations, data destruction and service
degradation; you only ever access data belonging to your own test accounts and devices; you
stop as soon as you have demonstrated the issue; and you give us a reasonable period —
ordinarily 90 days — to publish a fix before you disclose publicly.</p>
<p>If a third party brings action against you for work that genuinely followed this policy, we
will make it clear that your research was authorised.</p>

<h2 id="bounty">5. Rewards</h2>
<p>We are a very small independent developer and we do not operate a paid bug bounty. We can
offer prompt attention, honest credit in the release notes if you want it, and a real
conversation with the person who wrote the code. We would rather say that plainly than imply a
payment that is not coming.</p>

<h2 id="contact">6. Contact</h2>
<ul>
  <li>Email: <a href="mailto:{EMAIL}">{EMAIL}</a></li>
  <li>Machine-readable policy: <a href="/security.txt">{SITE['domain']}/security.txt</a></li>
</ul>
</section>"""

    return write("security/index.html", page(
        f"Security — {COMPANY}",
        f"Security and vulnerability disclosure policy for {COMPANY}: how to report an issue, "
        "what is in scope, and our safe harbour commitment.",
        body,
        canonical="/security/",
    ))


# --------------------------------------------------------------------------
# Terms
# --------------------------------------------------------------------------

def build_terms():
    body = f"""<section class="card legal">
  <div class="kicker">{e(COMPANY)}</div>
  <h1>Terms of Use</h1>
  <p class="meta-line">Last updated: {e(UPDATED)} · Applies to every {e(COMPANY)} app</p>

  <div class="note">
    <p><b>The short version.</b> The apps are licensed to you, not sold. Use them on your own
    devices, do not resell or reverse-engineer them, and understand that they come without a
    warranty. Purchases and refunds are handled by Apple and Google, not by us.</p>
  </div>

<h2 id="licence">1. Licence</h2>
<p>{e(COMPANY)} grants you a personal, non-exclusive, non-transferable, revocable licence to
use our applications on devices you own or control, in accordance with the usage rules of the
store you obtained the app from. This licence does not transfer ownership of the software.</p>

<h2 id="restrictions">2. What you may not do</h2>
<ul>
  <li>Copy, redistribute, resell, rent, lease or sublicense the app.</li>
  <li>Reverse-engineer, decompile or disassemble it, except where that right cannot lawfully
  be restricted.</li>
  <li>Remove or alter any proprietary notice.</li>
  <li>Use the app to break the law, or to interfere with any device or network you are not
  authorised to use.</li>
</ul>

<h2 id="purchases">3. Purchases and refunds</h2>
<p>All purchases are processed by Apple or Google under their own terms. We never see your
payment details. Refunds are handled by the store you bought from — use
<a href="https://reportaproblem.apple.com">reportaproblem.apple.com</a> for Apple, or your
Google Play order history for Android. We are not able to issue a refund directly.</p>

<h2 id="health">4. Health and fitness information</h2>
<p>Any health, fitness, fasting or nutrition information shown in our apps is for general
informational purposes only. It is not medical advice, and it is not a diagnosis, treatment or
professional recommendation. Consult a qualified healthcare provider before beginning any
fasting, dietary or exercise programme, and do not disregard professional advice because of
something an app showed you. If you have a medical condition, are pregnant, or are taking
medication, speak to a doctor first.</p>

<h2 id="security">5. Your data and your device</h2>
<p>Our apps store your data on your device rather than on our servers. That means we cannot
recover it for you. You are responsible for keeping your device secure and for backing up
anything you would not want to lose. Where an app uses a master password or a recovery key,
losing both means the data cannot be recovered by anyone, including us — that is a deliberate
property of the encryption, not a defect.</p>

<h2 id="availability">6. Availability and changes</h2>
<p>We may update, change or discontinue an app or any of its features. We aim not to break
things you rely on, but we do not guarantee that any app will remain available, compatible
with future operating systems, or unchanged.</p>

<h2 id="warranty">7. No warranty</h2>
<p>The apps are provided &ldquo;as is&rdquo; and &ldquo;as available&rdquo;, without warranty
of any kind, express or implied, including any implied warranty of merchantability, fitness
for a particular purpose or non-infringement. We do not warrant that an app will be
uninterrupted, error-free, or free of harmful components.</p>

<h2 id="liability">8. Limitation of liability</h2>
<p>To the fullest extent permitted by law, {e(COMPANY)} is not liable for any indirect,
incidental, special, consequential or punitive damages, or for any loss of data, profits or
goodwill, arising from your use of or inability to use an app. Where liability cannot be
excluded, it is limited to the amount you paid for the app in the twelve months before the
claim arose.</p>
<p>Nothing in these terms excludes liability that cannot lawfully be excluded, including
liability for death or personal injury caused by negligence, or for fraud. Some jurisdictions
do not allow certain exclusions, so parts of this section may not apply to you.</p>

<h2 id="apple">9. Apple-specific terms</h2>
<p>For apps obtained from the Apple App Store, you acknowledge that these terms are between you
and {e(COMPANY)} only, not with Apple; that Apple has no obligation to provide support for the
app; that Apple is not responsible for addressing any claim relating to the app; and that Apple
and its subsidiaries are third-party beneficiaries of these terms, with the right to enforce
them. Your use is also subject to the Apple Media Services Terms and Conditions. If you do not
have your own end-user licence agreement in place, Apple's standard
<a href="https://www.apple.com/legal/internet-services/itunes/dev/stdeula/">Licensed
Application End User License Agreement</a> applies in addition to these terms.</p>

<h2 id="google">10. Google Play-specific terms</h2>
<p>For apps obtained from Google Play, your use is also subject to the Google Play Terms of
Service. Google is not a party to these terms and has no responsibility for the app.</p>

<h2 id="termination">11. Termination</h2>
<p>This licence ends automatically if you breach these terms. You can end it at any time by
deleting the app from your devices.</p>

<h2 id="law">12. Governing law</h2>
<p>These terms are governed by the laws applicable at {e(COMPANY)}'s place of business,
without regard to conflict-of-law rules. Nothing here removes any mandatory consumer
protection you have under the law of the country you live in.</p>

<h2 id="contact">13. Contact</h2>
<p>Questions about these terms: <a href="mailto:{EMAIL}">{EMAIL}</a></p>
</section>"""

    return write("terms/index.html", page(
        f"Terms of Use — {COMPANY}",
        f"Terms of use covering all {COMPANY} apps, including licence, refunds, warranty and "
        "Apple App Store and Google Play requirements.",
        body,
    ))


def build_404():
    links = "\n".join(
        f'    <a class="btn" href="/apps/{a["slug"]}/">{e(a["name"])}</a>' for a in APPS
    )
    body = f"""<section class="card hero">
  <div class="kicker">404</div>
  <h1>That page isn't here.</h1>
  <p class="lede">The link may be out of date. Everything we publish is one of the pages
  below.</p>
  <div class="cta" style="justify-content:center">
    <a class="btn primary" href="/">Home</a>
    <a class="btn" href="/support/">Support</a>
    <a class="btn" href="/privacy/">Privacy</a>
  </div>
</section>

<section class="card">
  <div class="kicker">Our apps</div>
  <h2>Looking for one of these?</h2>
  <div class="cta">
{links}
  </div>
</section>"""
    return write("404.html", page(
        "Page not found — " + COMPANY,
        "The page you were looking for could not be found.",
        body,
    ))


# --------------------------------------------------------------------------
# Static assets and host configuration
# --------------------------------------------------------------------------

FAVICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#7a63ff"/><stop offset="1" stop-color="#00d1ff"/>'
    '</linearGradient></defs>'
    '<rect width="64" height="64" rx="15" fill="#07080c"/>'
    '<rect x="13" y="13" width="38" height="38" rx="11" fill="url(#g)"/>'
    "</svg>\n"
)


def build_assets():
    """App artwork, favicon, security.txt and the Cloudflare Pages header rules."""
    copied = []
    dest = os.path.join(ROOT, "assets", "icons")
    shutil.rmtree(dest, ignore_errors=True)
    if APP_ART:
        os.makedirs(dest, exist_ok=True)
        for slug, fname in sorted(APP_ART.items()):
            shutil.copy2(os.path.join(ICON_SRC, fname), os.path.join(dest, fname))
            copied.append(f"assets/icons/{fname}")

    write("favicon.svg", FAVICON)

    sec = (f"Contact: mailto:{EMAIL}\n"
           f"Preferred-Languages: en\n"
           f"Canonical: https://{SITE['domain']}/security.txt\n"
           f"Policy: https://{SITE['domain']}/security/\n")
    write("security.txt", sec)
    # Cloudflare Pages has historically dropped dot-directories from a
    # deployment, so /security.txt is the copy that is certain to be served and
    # the RFC 9116 location is mirrored here plus redirected below.
    write(".well-known/security.txt", sec)
    write("_redirects", "/.well-known/security.txt  /security.txt  301\n")

    # One inline script on the whole site; pin it by hash rather than opening
    # script-src up to 'unsafe-inline'. Inline <style> carries the per-page
    # accent and differs on every page, so it stays on 'unsafe-inline'.
    digest = base64.b64encode(hashlib.sha256(HOME_JS.encode("utf-8")).digest()).decode()
    csp = ("default-src 'none'; "
           "img-src 'self' data:; "
           "style-src 'self' 'unsafe-inline'; "
           f"script-src 'sha256-{digest}'; "
           "font-src 'self'; "
           "base-uri 'none'; "
           "form-action 'none'; "
           "frame-ancestors 'none'")
    write("_headers", f"""/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()
  Cross-Origin-Opener-Policy: same-origin
  Content-Security-Policy: {csp}
  Strict-Transport-Security: max-age=31536000; includeSubDomains

/assets/*
  Cache-Control: public, max-age=3600

/security.txt
  Content-Type: text/plain; charset=utf-8

/.well-known/security.txt
  Content-Type: text/plain; charset=utf-8
""")
    return copied + ["favicon.svg", "security.txt", ".well-known/security.txt",
                     "_redirects", "_headers"]


# --------------------------------------------------------------------------

def build_sitemap():
    paths = ["/", "/support/", "/privacy/", "/terms/", "/data-deletion/",
             "/kids/", "/accessibility/", "/security/"]
    for a in APPS:
        paths += [f"/apps/{a['slug']}/", f"/apps/{a['slug']}/support/",
                  f"/apps/{a['slug']}/privacy/"]
    urls = "\n".join(
        f"  <url><loc>https://{SITE['domain']}{p}</loc></url>" for p in paths
    )
    write("sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          f"{urls}\n</urlset>\n")
    write("robots.txt",
          f"User-agent: *\nAllow: /\n\nSitemap: https://{SITE['domain']}/sitemap.xml\n")
    return len(paths)


def main():
    # Clean generated app pages so a removed app does not linger.
    apps_dir = os.path.join(ROOT, "apps")
    if os.path.isdir(apps_dir):
        shutil.rmtree(apps_dir)

    written = [write("assets/site.css", CSS.strip() + "\n")]
    write(".nojekyll", "")

    written.append(build_home())
    for app in APPS:
        written.append(build_app_page(app))
        written.append(build_app_privacy(app))
        written.append(build_app_support(app))
    written.append(build_privacy_hub())
    written.append(build_support_hub())
    written.append(build_terms())
    written.append(build_data_deletion())
    written.append(build_kids())
    written.append(build_accessibility())
    written.append(build_security())
    written.append(build_404())
    written += build_assets()
    count = build_sitemap()

    print(f"Generated {len(written)} pages + sitemap ({count} URLs), robots.txt.")
    for w in written:
        print("  " + w)


if __name__ == "__main__":
    main()
