# All Togetharr — Implementation Plan

## Executive Summary

A local-first, privacy-focused management dashboard that unifies self-hosted media stack services (Sonarr, Radarr, Plex, Jellyfin, qBittorrent, etc.) into a single pane of glass. Built with an Apple-inspired minimalist aesthetic using Next.js, TypeScript, Prisma + SQLite, Tailwind, shadcn/ui, and Zustand.

**Current state:** Design prototype with 3 HTML mockups, design system spec, and scaffolded source tree. No runnable application code yet.

---

## Phase 1: Project Scaffolding (Priority)

**Goal:** Get a runnable Next.js app with the correct design system.

| Task | Details |
|------|---------|
| `package.json` | Next.js 14+, TypeScript, Prisma, Zustand, Docker dependencies |
| `next.config.ts` | App Router, image optimization, proxy rewrites |
| `tsconfig.json` | Path aliases (`@/app`, `@/components`, `@/lib`, `@/services`, `@/stores`) |
| `tailwind.config.ts` | **Exact color tokens from DESIGN.md** — `surface`, `surface-container-low`, `surface-container-lowest`, `primary`, `outline-variant`, `error`, etc. (40+ tokens) |
| Font setup | Inter loaded from Google Fonts, with tracking variants (`headline`, `body`, `label`) |
| `app/layout.tsx` | Root layout with Inter, dark mode class strategy, Tailwind preflight |
| `app/globals.css` | Custom scrollbar, `pulse-soft` animation (for health dots), `no-scrollbar` utility |

### Design Tokens (from DESIGN.md)

| Token | Value | Usage |
|-------|-------|-------|
| `surface` | `#F9F9FB` | Base background |
| `surface-container-low` | `#F2F4F6` | Section backgrounds |
| `surface-container-lowest` | `#FFFFFF` | Widget/card backgrounds |
| `primary` | `#5F5E60` | Primary actions, focus states |
| `error` | `#9F403D` | Alert states |
| `outline-variant` | `#ACB3B8` | Ghost borders (15% opacity) |
| `inverse-surface` | `#0C0E10` | Deep contrast (never pure black) |
| `secondary` | `#5E5F63` | Secondary actions |
| `tertiary` | `#5F5F5F` | Tertiary actions |
| `on-surface` | `#2D3338` | Primary text |
| `on-surface-variant` | `#596065` | Secondary text |
| `on-background` | `#2D3338` | Body text |
| `outline` | `#757C81` | Outlines |

### Component Specs

- **Ghost inputs:** No background, only `outline-variant` bottom stroke, `primary` focus state
- **Health dots:** 8px circles with `pulse-soft` animation, 4px outer glow
- **Buttons:** Primary (solid `primary` fill), Secondary (`surface-container-high`), Tertiary/Ghost (no fill)
- **Cards:** `surface-container-lowest` bg, `xl` (0.75rem) radius, no borders, 16–24px padding
- **Glassmorphism:** `surface-container-lowest` at 80% opacity + `backdrop-blur(20px)` for overlays

---

## Phase 2: Database Schema (Prisma + SQLite)

**Goal:** Local-first persistence for service configurations.

```prisma
model Service {
  id           String   @id @default(cuid())
  name         String   // e.g. "Sonarr", "Plex"
  type         String   // "arr", "media-server", "download-client", "indexer"
  enabled      Boolean  @default(false)
  connections  Connection[]
  createdAt    DateTime @default(now())
  updatedAt    DateTime @updatedAt
}

model Connection {
  id            String   @id @default(cuid())
  serviceId     String
  service       Service  @relation(fields: [serviceId], references: [id])
  label         String   // e.g. "Home Server", "Office NAS"
  baseUrl       String   // e.g. "http://192.168.1.100:8989"
  apiKey        String   // encrypted in DB
  apiVersion    String?
  categories    Category[]
  healthStatus  String   @default("unknown") // "online", "offline", "error", "unknown"
  lastChecked   DateTime?
  createdAt     DateTime @default(now())
  updatedAt     DateTime @updatedAt
}

model Category {
  id            String   @id @default(cuid())
  connectionId  String
  connection    Connection @relation(fields: [connectionId], references: [id])
  name          String   // e.g. "movies", "tv", "books"
  rootPath      String?  // e.g. "/media/movies"
  protocol      String?  // "nfs", "smb", "http"
}

model Settings {
  id              String   @id @default(cuid())
  key             String   @unique // e.g. "dashboard.layout", "theme"
  value           String   // JSON string
  updatedAt       DateTime @updatedAt
}
```

---

## Phase 3: State Management (Zustand)

**Goal:** Client-side state for dashboard, onboarding, and settings.

| Store | Purpose |
|-------|---------|
| `useServicesStore` | List of connected services, their health status, enable/disable toggles |
| `useDashboardStore` | Widget visibility, layout preferences, filter state |
| `useOnboardingStore` | Multi-step wizard progress, selected services, connection metadata |
| `useSettingsStore` | Settings overlay open/close, active tab, service lifecycle actions |
| `useProxyStore` | Proxy request state, error handling, rate limiting |

---

## Phase 4: API Routes

**Goal:** Server-side proxy that forwards raw API calls per-service.

| Route | Purpose |
|-------|---------|
| `GET /api/health` | Aggregated health status of all connected services |
| `GET /api/services` | List all services with their connections |
| `GET/POST/PUT/DELETE /api/services/[id]` | CRUD for service configurations |
| `GET/POST /api/proxy/[service]/[...path]` | **Raw proxy** — forwards requests to Sonarr, Radarr, Plex, etc. with stored API key injected. Handles CORS by proxying server-side. |

### Proxy Behavior

1. Reads `Connection` from Prisma by service ID
2. Injects `apiKey` into request headers
3. Forwards the full path (e.g., `/api/v3/series`, `/api/movie`)
4. Returns the raw response from the target service
5. Caches health checks with configurable interval

---

## Phase 5: UI Components

**Goal:** Reusable components matching the design system.

| Component | Description |
|-----------|-------------|
| `HealthDot` | 8px circle with `pulse-soft` animation, color based on status |
| `ServiceChip` | Compact state badge (e.g., "ONLINE", "OFFLINE", "ERROR") |
| `GhostInput` | Transparent bg, `outline-variant` bottom stroke, `primary` focus |
| `SurfaceCard` | `surface-container-lowest` bg, `xl` radius, no borders |
| `GlassOverlay` | 80% opacity + `backdrop-blur(20px)` for settings drawer |
| `MediaRow` | Hover state uses `surface-container-low`, no dividers |
| `StatusLabel` | All-caps, `tracking-[0.1em]`, `label` font family |

---

## Phase 6: Pages & Flows

**Goal:** Three main screens matching the HTML prototypes.

| Page | Route | Key Features |
|------|-------|-------------|
| **Onboarding Wizard** | `/onboarding` | 3-step flow: (1) Select services, (2) Enter connection metadata (URL, port, API key), (3) Test connection → save |
| **Dashboard** | `/dashboard` | Three-pane layout: left nav rail (service health), central content (media feed, transfer monitor, request queue), right rail (system metrics, request management) |
| **Settings Overlay** | (persistent, not a route) | Glassmorphism overlay, category tabs, add/remove/reconfigure services, toggle enabled state |

### Dashboard Layout

```
┌─────────────────────────────────────────────────────┐
│  Top Nav: "All Togetharr" + user controls           │
├──────────┬──────────────────────────┬───────────────┤
│          │                          │               │
│ Left     │  Central Content         │  Right Rail   │
│ Rail     │                          │               │
│ (Nav +   │  • Hero stats            │  System       │
│  Health) │  • Media Feed            │  Metrics      │
│          │  • Transfer Monitor      │  Request Mgmt │
│          │  • Calendar              │               │
│          │                          │               │
└──────────┴──────────────────────────┴───────────────┘
```

---

## Phase 7: Docker Deployment

**Goal:** One-command local deployment.

| File | Purpose |
|------|---------|
| `Dockerfile` | Node 20 Alpine, Next.js production build, SQLite bundled |
| `docker-compose.yml` | Next.js container + volume for SQLite data directory |
| `.env.local` | `DATABASE_URL=file:/data/sqlite.db` |

---

## Supported Services (Proxy Targets)

| Category | Services |
|----------|----------|
| **Arr Suite** | Sonarr, Radarr, Prowlarr |
| **Request Manager** | Jellyseerr |
| **Media Servers** | Plex, Emby, Jellyfin |
| **Download Clients** | qBittorrent, Transmission |

Each gets its own proxy route segment: `/api/proxy/[service]/[...path]` where `[service]` is one of: `sonarr`, `radarr`, `prowlarr`, `jellyseerr`, `plex`, `emby`, `jellyfin`, `qbittorrent`, `transmission`.

---

## Target File Structure

```
src/
├── app/
│   ├── api/
│   │   ├── health/
│   │   │   └── route.ts
│   │   ├── proxy/
│   │   │   └── [service]/
│   │   │       └── [...path]/
│   │   │           └── route.ts
│   │   └── services/
│   │       └── [id]/
│   │           └── route.ts
│   ├── dashboard/
│   │   └── page.tsx
│   ├── onboarding/
│   │   └── page.tsx
│   ├── layout.tsx
│   └── globals.css
├── components/
│   ├── dashboard/
│   │   └── widgets/
│   │       ├── MediaFeed.tsx
│   │       ├── TransferMonitor.tsx
│   │       └── RequestQueue.tsx
│   ├── layout/
│   │   ├── navigation/
│   │   │   ├── TopNav.tsx
│   │   │   └── LeftRail.tsx
│   │   └── rails/
│   │       └── RightRail.tsx
│   ├── onboarding/
│   │   └── steps/
│   │       ├── ServiceSelection.tsx
│   │       ├── ConnectionSetup.tsx
│   │       └── ConnectionTest.tsx
│   ├── settings/
│   │   └── SettingsOverlay.tsx
│   └── ui/
│       ├── HealthDot.tsx
│       ├── ServiceChip.tsx
│       ├── GhostInput.tsx
│       ├── SurfaceCard.tsx
│       └── GlassOverlay.tsx
├── lib/
│   ├── prisma.ts          // Prisma client singleton
│   └── proxy.ts           // Proxy utility (headers, error handling)
├── services/
│   └── serviceRegistry.ts // Service type definitions, proxy config
└── stores/
    ├── useServicesStore.ts
    ├── useDashboardStore.ts
    ├── useOnboardingStore.ts
    ├── useSettingsStore.ts
    └── useProxyStore.ts
prisma/
└── schema.prisma
```

---

## Design System Quick Reference

### Typography

| Style | Font | Tracking | Color |
|-------|------|----------|-------|
| Display | Inter | `-0.02em` | `#1D1D1F` |
| Headlines | Inter | `-0.01em` | `#1D1D1F` |
| Body | Inter | normal | `#6E6E73` |
| Labels | Inter | `0.1em` (all-caps) | `#596065` |

### Design Rules

| Rule | Description |
|------|-------------|
| **No-line rule** | No solid borders — use tonal surface shifts |
| **Ghost borders** | `outline-variant` at 15% opacity (accessibility fallback) |
| **Glassmorphism** | `surface-container-lowest` at 80% + `backdrop-blur(20px)` |
| **Ambient shadows** | 32–64px blur, 4–8% opacity, tinted `on_surface` |
| **Corner radius** | `xl` (0.75rem) for widgets, `md` (0.375rem) for nested |
| **Status chips** | `9999px` (full) rounding |
| **No pure black** | Use `inverse-surface` (`#0C0E10`) for deep contrast |
| **No icons without purpose** | Every icon must be accompanied by text or have a universally understood function |
| **Asymmetrical layouts** | Wide 2/3 widget next to narrow 1/3 health monitor |
| **Embrace whitespace** | If a layout feels "empty," increase typography size rather than adding a border |

---

## Prototype Reference

Three HTML prototypes exist in `stitch-export/all-togetharr-media-dashboard/`:

| File | Description |
|------|-------------|
| `main-dashboard.html` | Three-pane operations view (left nav rail, central content, right metrics) |
| `onboarding-wizard.html` | 3-step service connection wizard (select → configure → test) |
| `settings-sidebar.html` | Persistent overlay for managing connected services |

All prototypes use Tailwind CSS (CDN), Inter font, Material Symbols, and the shared design token palette defined in `DESIGN.md`.
