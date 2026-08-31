# flowlabapps.com

The Flowlab Apps website. Every page here is generated from a single data file, so adding
an app or fixing a fact means editing one place and re-running one command.

## Build

```bash
python3 _build/build.py
```

No dependencies beyond Python 3. The script writes static HTML to the repo root, which is
what gets served. Both `href` and `src` are emitted page-relative, so the site renders
correctly when opened directly from Finder over `file://`, served from a domain root, or
hosted under a subpath. `.nojekyll` is present so the host serves files exactly as generated.

**The generated HTML is committed**, so the host does not need to run anything — see
Deploying below.

## Editing

- **`_build/apps.json`** — all app content: names, taglines, features, privacy facts,
  permissions, FAQs. This is the file you edit.
- **`_build/build.py`** — templates, stylesheet and page structure. Edit this to change how
  pages look, not what they say.
- **`_build/icons/<slug>.png|jpg`** — each app's real store icon, downscaled to 256&nbsp;px.
  The build copies these to `assets/icons/`. An app with no file here falls back to the drawn
  line mark in `MARKS`, so a new app can go up before its artwork exists.

Everything else in the repo is generated output. Do not hand-edit the HTML; the next build
overwrites it.

### Adding an app

Append an entry to the `apps` array in `apps.json` and re-run the build. It picks up a
detail page, a privacy policy, a support page, a home-page card, footer links and a sitemap
entry automatically.

Required fields: `slug`, `name`, `tagline`, `category`, `platforms`, `status`,
`status_kind` (`live` | `soon` | `dev`), `bundle_ids`, `accent` (two hex colors), `glyph`,
`summary`, `long`, `features`, `privacy`, `support`. Optional: `privacy.store_note` for an
app whose network behaviour needs a word of qualification next to the store declarations.

A `category` beginning with `Games` files the app under the Games filter on the home page.

To add its icon, drop the 1024&nbsp;px store icon through:

```bash
sips -Z 256 /path/to/AppIcon-1024.png --out _build/icons/<slug>.png
```

If the icon has no alpha channel (`sips -g hasAlpha`), save it as `.jpg` at quality 86
instead — it is roughly a quarter of the size and the build picks up either extension.

### Removing an app

Delete its entry from `apps.json` and rebuild — the build clears `apps/` first, so the old
pages disappear. If that app was already published to a store, leave its privacy policy
reachable until the listing is gone.

## Deploying (Cloudflare Pages)

The generated HTML is committed, so Cloudflare does **not** need to run Python. Connect the
repo and set:

| Setting | Value |
|---|---|
| Framework preset | None |
| Build command | *(leave blank)* |
| Build output directory | `/` |

`_headers` (security headers, including a CSP that pins the one inline script by hash) and
`_redirects` are read by Cloudflare Pages automatically. No `CNAME` file is needed — the
custom domain is set in the Pages dashboard, unlike GitHub Pages.

Cloudflare has historically dropped dot-directories from a deployment, so `/security.txt` is
the canonical copy and `/.well-known/security.txt` is both mirrored and redirected to it.
The same caveat matters later for `/.well-known/apple-app-site-association` if you ever add
Universal Links — verify it is actually served before relying on it.

## URLs to give the stores

Both Apple and Google require a privacy policy URL, and Apple additionally requires a
support URL. Each app has its own, and they are stable:

- Support: `https://flowlabapps.com/apps/<slug>/support/`
- Privacy: `https://flowlabapps.com/apps/<slug>/privacy/`

The site-wide `/privacy/` and `/support/` pages still work and cover every app, so any
listing already pointing at them stays valid. Google Play's Data safety form also asks for a
data-deletion URL:

- Data deletion: `https://flowlabapps.com/data-deletion/`

Supporting pages a reviewer may ask for: `/kids/` (COPPA, Play Families, Kids Category),
`/terms/` (EULA), `/accessibility/` and `/security/`.

## Keeping the policies honest

The privacy text in `apps.json` was written from what each app's source actually does —
permissions declared in the manifests and plists, dependencies in the package files, and the
absence of any analytics, advertising or networking SDK. If an app gains a permission, a
network call or a third-party SDK, update its `privacy` block **before** that version ships.
A privacy policy that is out of date is a store rejection, and worse, a false statement.
