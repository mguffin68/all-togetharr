# All Togetharr Copilot Instructions

## Current repository state

- Treat this repository as a product/design prototype first. The checked-in artifacts are:
  - `README.md` for product scope and the intended production stack
  - `DESIGN.md` for the visual system and interaction rules
  - `stitch-export/all-togetharr-media-dashboard/` for the current screen prototypes
- The README describes the planned implementation stack (`Next.js` App Router, `TypeScript`, `Prisma` + `SQLite`, `Tailwind`, `shadcn/ui`, `Zustand`, Docker), but that application source is not checked in yet.
- Do not assume there is already a runnable Next.js app, package manager setup, Prisma schema, or test suite in the tree.

## Commands

- There are currently **no checked-in build, test, or lint commands**. The repo has no `package.json`, test runner config, or linter config.
- There is currently **no single-test command** because no test suite or test files are present.
- `README.md` mentions:

```bash
docker-compose up -d
```

- Treat that as aspirational documentation for the intended app; there is no compose file in this snapshot.

## High-level architecture

- The current codebase expresses the product through three prototype screens:
  - `stitch-export/all-togetharr-media-dashboard/onboarding-wizard.html`: multi-step service selection and connection setup
  - `stitch-export/all-togetharr-media-dashboard/main-dashboard.html`: the main operations view
  - `stitch-export/all-togetharr-media-dashboard/settings-sidebar.html`: the persistent configuration drawer / admin rail
- The intended product model, assembled from `README.md` and the prototypes, is a **local-first dashboard for a self-hosted media stack**. It aggregates:
  - media managers and indexers such as Sonarr, Radarr, Jellyseerr, and Prowlarr
  - media servers such as Plex, Jellyfin, and Emby
  - download clients such as qBittorrent or Transmission
- The main dashboard prototype is organized as a **three-region layout**:
  - a left rail for primary navigation and service health
  - a central content area for hero content, recent media, and calendar data
  - a right rail for system metrics and request-management summaries
- The onboarding flow assumes per-service connection metadata such as **local URL/IP, port, and API key/token**, plus an explicit "test connection" step before continuing.
- The settings screen is modeled as a **persistent overlay**, not a separate page. It focuses on toggling connected services, exposing category tabs, and adding new service integrations from the same shell.
- If real application code is added later, keep these concerns separated:
  - onboarding / service discovery
  - dashboard aggregation and presentation
  - settings / service lifecycle management
  - local persistence of service configuration and credentials

## Key conventions

- Use the **shared design tokens** already repeated across the exported HTML files. The Tailwind color names (`surface`, `surface-container-low`, `surface-container-lowest`, `primary`, `outline-variant`, etc.) are the canonical palette for this repo.
- Follow the **"no-line" rule** from `DESIGN.md`: define sections with tonal surface changes, not hard divider borders. Only use very faint outline variants when structure is absolutely necessary.
- Preserve the repo's **editorial / Apple-inspired layout language**:
  - asymmetrical or bento-style grids
  - generous whitespace
  - bold, tight-tracked headlines
  - all-caps, high-tracking metadata labels
- Use **surface layering** rather than shadow-heavy cards. Elevated elements should usually read as stacked paper or glass, not as dark floating panels.
- Floating admin surfaces use **glassmorphism**: translucent backgrounds plus backdrop blur. The settings drawer and right-side dashboard rail are the clearest references.
- Inputs should follow the **ghost-input** pattern from the onboarding screen: transparent background, only a bottom rule, and a stronger primary-colored focus state.
- Service health should be communicated with **small glowing dots and compact state chips**, not dense tables.
- The current prototypes use **Material Symbols** loaded from Google Fonts, while the README names Lucide for the future app stack. If you introduce a real icon system, call out that migration explicitly instead of mixing icon sets silently.
- Typography is consistently **Inter**. Reuse its tracking patterns from `DESIGN.md` rather than defaulting to ordinary Tailwind text styles.
