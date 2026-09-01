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

## The one way to break this site

**Cloudflare runs no build command.** It serves exactly the HTML that is committed. So
editing `_build/apps.json` and committing *without re-running the build* deploys the old
pages while the data file says something new — silently, with a green tick in the
Cloudflare dashboard and no error anywhere.

That is not hypothetical: the PulseFast page advertised "14:10, 18:6, 20:4 presets and a
custom target from 10 to 24 hours" for weeks. The app has never had those. Its real presets
run 13–72h with custom goals to 168h. For a Health & Fitness listing, marketing copy that
understates a seven-day fasting ceiling is an App Review problem, not a typo.

**After any edit to `apps.json`, run the build before committing:**

```bash
python3 _build/build.py
git add -A
```

A pre-commit hook enforces this. Install it once per clone:

```bash
bash _build/hooks/install.sh
```

It rebuilds, and refuses the commit if that produces changes you have not staged, naming
the files. `git commit --no-verify` bypasses it, which you should not need.

## Deploying (Cloudflare Pages)

The generated HTML is committed, so Cloudflare does **not** need to run Python. Connect the
repo and set:

| Setting | Value |
|---|---|
| Framework preset | None |
| Build command | *(leave blank)* |
| Build output directory | `/` |

Deploys are Git-driven: a push to `main` triggers a Cloudflare build and promotes it
automatically. Earlier deployments in the dashboard marked *"Manually deployed"* predate
that connection. Verified 31 Aug 2026 — a push went live without any manual step.

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
