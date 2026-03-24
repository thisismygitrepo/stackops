# Hosting Your Documentation

This guide covers local preview and hosting options for the repository's Zensical-powered documentation site.

!!! note
    Machineconfig builds and deploys docs with `zensical`, configured in `zensical.toml`. If you install docs tooling manually instead of running `uv sync --group dev`, install `zensical` and `mkdocstrings-python`.

---

## Local Development

### Quick Serve

```bash
uv run zensical serve
```

Open `http://127.0.0.1:8000/machineconfig/`. The site root redirects there because `site_url` includes `/machineconfig/`.

### Custom Port

```bash
uv run zensical serve --dev-addr=0.0.0.0:8080
```

### Open in Browser

Open the preview automatically in your default browser:

```bash
uv run zensical serve --open
```

### Build Static Files

```bash
uv run zensical build
```

Creates a `site/` directory with static HTML files.

If you removed or renamed pages, delete `site/` before rebuilding so stale files don't linger from older outputs.

---

## Free Hosting Options

### 1. GitHub Pages (Recommended)

**Best for**: Open source projects on GitHub

**Pros**:
- Completely free
- Automatic HTTPS
- Custom domain support
- Native deployment target for GitHub Actions

**Setup**:

=== "Build locally"

    ```bash
    uv run zensical build
    ```

    This generates `site/`, which you can publish with GitHub Pages or any other static host.

=== "GitHub Actions (Automated)"

    Create `.github/workflows/docs.yml`:

    ```yaml
    name: Deploy Docs
    on:
      push:
        branches: [main]
        paths:
          - 'docs/**'
          - 'docs_fragments/**'
          - 'zensical.toml'
          - 'pyproject.toml'
          - 'uv.lock'
          - 'src/**'
          - '.github/workflows/docs.yml'
      workflow_dispatch:

    permissions:
      contents: read
      pages: write
      id-token: write

    concurrency:
      group: pages
      cancel-in-progress: true

    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4

          - name: Setup Python
            uses: actions/setup-python@v5
            with:
              python-version: '3.13'

          - name: Install uv
            uses: astral-sh/setup-uv@v4

          - name: Configure GitHub Pages
            uses: actions/configure-pages@v5

          - name: Install dependencies
            run: uv sync --group dev

          - name: Build site
            run: rm -rf site && uv run zensical build

          - name: Upload Pages artifact
            uses: actions/upload-pages-artifact@v3
            with:
              path: site

      deploy:
        runs-on: ubuntu-latest
        needs: build
        environment:
          name: github-pages
          url: ${{ steps.deployment.outputs.page_url }}
        steps:
          - id: deployment
            uses: actions/deploy-pages@v4
    ```

**Enable GitHub Pages**:

1. Go to repository **Settings** → **Pages**
2. Source: **GitHub Actions**
3. Save

**Your docs will be at**: `https://thisismygitrepo.github.io/machineconfig/`

---

### 2. Cloudflare Pages

**Best for**: Fast global CDN, unlimited bandwidth

**Pros**:
- Unlimited bandwidth (free tier)
- Global CDN (300+ locations)
- Automatic HTTPS
- Custom domains
- Preview deployments for PRs

**Setup**:

1. Go to [Cloudflare Pages](https://pages.cloudflare.com/)
2. Connect your GitHub repository
3. Configure build settings:

| Setting | Value |
|---------|-------|
| Build command | `pip install . zensical mkdocstrings-python && zensical build` |
| Build output directory | `site` |
| Root directory | `/` |

**Or use a build script** - create `build_docs.sh`:

```bash
#!/bin/bash
pip install uv
uv sync --group dev
uv run zensical build
```

Then set build command to: `bash build_docs.sh`

---

### 3. Netlify

**Best for**: Easy setup, good free tier

**Pros**:
- 100GB bandwidth/month (free)
- Automatic HTTPS
- Custom domains
- Deploy previews
- Form handling

**Setup**:

1. Go to [Netlify](https://www.netlify.com/)
2. Import your GitHub repository
3. Configure:

| Setting | Value |
|---------|-------|
| Build command | `pip install . zensical mkdocstrings-python && zensical build` |
| Publish directory | `site` |

**Or create `netlify.toml`**:

```toml
[build]
  command = "pip install . zensical mkdocstrings-python && zensical build"
  publish = "site"

[build.environment]
  PYTHON_VERSION = "3.11"
```

---

### 4. Vercel

**Best for**: Fast deployments, serverless functions

**Pros**:
- Unlimited bandwidth (fair use)
- Global edge network
- Automatic HTTPS
- Preview deployments

**Setup**:

1. Go to [Vercel](https://vercel.com/)
2. Import repository
3. Create `vercel.json`:

```json
{
  "buildCommand": "zensical build",
  "outputDirectory": "site",
  "installCommand": "pip install . zensical mkdocstrings-python"
}
```

---

### 5. GitLab Pages

**Best for**: GitLab users

**Pros**:
- Free for public/private repos
- Automatic HTTPS
- CI/CD integration

**Setup** - create `.gitlab-ci.yml`:

```yaml
image: python:3.11

pages:
  stage: deploy
  script:
    - pip install . zensical mkdocstrings-python
    - zensical build
    - mv site public
  artifacts:
    paths:
      - public
  only:
    - main
```

---

### 6. Read the Docs

**Best for**: Python projects that want hosted docs and version management

**Pros**:
- Free for open source
- Automatic versioning
- PDF/ePub generation
- Search across versions

**Setup**:

1. Go to [Read the Docs](https://readthedocs.org/)
2. Import your repository
3. Create `.readthedocs.yaml`:

```yaml
version: 2

build:
  os: ubuntu-24.04
  tools:
    python: "3.13"
  jobs:
    install:
      - pip install . zensical mkdocstrings-python
    build:
      html:
        - mkdir -p $READTHEDOCS_OUTPUT/html
        - zensical build
        - cp -r site/. $READTHEDOCS_OUTPUT/html/
```

Read the Docs is still oriented around MkDocs and Sphinx, so with Zensical you provide an explicit build job that writes HTML into `$READTHEDOCS_OUTPUT/html/`.

---

### 7. Render

**Best for**: Simple static hosting

**Pros**:
- 100GB bandwidth/month
- Automatic HTTPS
- Custom domains

**Setup**:

1. Go to [Render](https://render.com/)
2. New → Static Site
3. Connect repository
4. Configure:

| Setting | Value |
|---------|-------|
| Build Command | `pip install . zensical mkdocstrings-python && zensical build` |
| Publish Directory | `site` |

---

### 8. Surge.sh

**Best for**: Quick CLI deployments

**Pros**:
- Simple CLI
- Free custom domains
- Unlimited publishing

**Setup**:

```bash
# Install surge
npm install -g surge

# Build docs
uv run zensical build

# Deploy
cd site && surge
```

First time will prompt for email/password. Your docs will be at `https://random-name.surge.sh`

**Custom domain**:

```bash
surge site/ yourdomain.surge.sh
```

---

### 9. Firebase Hosting

**Best for**: Google ecosystem users

**Pros**:
- 10GB storage, 360MB/day transfer (free)
- Global CDN
- Custom domains

**Setup**:

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login
firebase login

# Initialize
firebase init hosting

# Build docs
uv run zensical build

# Deploy
firebase deploy --only hosting
```

Configure `firebase.json`:

```json
{
  "hosting": {
    "public": "site",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"]
  }
}
```

---

## Comparison Table

| Platform | Bandwidth | Custom Domain | HTTPS | Build Time | Best For |
|----------|-----------|---------------|-------|------------|----------|
| **GitHub Pages** | 100GB/mo | Yes | Yes | ~1 min | GitHub projects |
| **Cloudflare Pages** | Unlimited | Yes | Yes | ~30 sec | Performance |
| **Netlify** | 100GB/mo | Yes | Yes | ~1 min | Ease of use |
| **Vercel** | Unlimited* | Yes | Yes | ~30 sec | Speed |
| **GitLab Pages** | Unlimited | Yes | Yes | ~2 min | GitLab users |
| **Read the Docs** | Unlimited | Yes | Yes | ~2 min | Versioned docs |
| **Render** | 100GB/mo | Yes | Yes | ~1 min | Simplicity |
| **Surge** | Unlimited | Yes | Yes | Instant | Quick deploys |
| **Firebase** | 360MB/day | Yes | Yes | ~1 min | Google users |

*Fair use policy applies

---

## Custom Domain Setup

Most platforms follow similar steps:

1. **Add domain in platform settings**
2. **Configure DNS**:
   
   For apex domain (example.com):
   ```
   A     @     185.199.108.153  (GitHub Pages IP)
   A     @     185.199.109.153
   A     @     185.199.110.153
   A     @     185.199.111.153
   ```
   
   For subdomain (docs.example.com):
   ```
   CNAME docs  thisismygitrepo.github.io
   ```

3. **Wait for DNS propagation** (up to 24 hours)
4. **Enable HTTPS** in platform settings

---

## Recommended Setup

For **machineconfig**, I recommend **GitHub Pages** with GitHub Actions:

1. **Free** and integrated with your repo
2. **Automatic deploys** on every push
3. **No configuration** needed beyond the workflow file
4. **Custom domain** support when ready

### Quick Start

```bash
# Preview locally
uv run zensical serve

# Deploy after pushing to main
git push origin main

# Your docs are live at:
# https://thisismygitrepo.github.io/machineconfig/
```

---

## Local Network Sharing

Share docs on your local network:

```bash
# Find your local IP
ip addr | grep "inet " | grep -v 127.0.0.1

# Serve on all interfaces
uv run zensical serve --dev-addr=0.0.0.0:8000
```

Others on your network can access at `http://YOUR_IP:8000/machineconfig/`

---

## Docker Deployment

For self-hosted scenarios:

```dockerfile
FROM python:3.13-slim

WORKDIR /docs
COPY . .

RUN pip install . zensical mkdocstrings-python
RUN zensical build

FROM nginx:alpine
COPY --from=0 /docs/site /usr/share/nginx/html
EXPOSE 80
```

Build and run:

```bash
docker build -t machineconfig-docs .
docker run -p 8080:80 machineconfig-docs
```
