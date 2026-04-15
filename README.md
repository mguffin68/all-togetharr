# All Togetharr

### Executive Overview
**All Togetharr** is a streamlined, local-first management dashboard designed to unify the self-hosted media stack. Built with an **Apple-inspired minimalist aesthetic**, it provides a single pane of glass for monitoring and configuring the most popular media automation and streaming services. 

Unlike cloud-dependent alternatives, All Togetharr prioritizes **privacy and performance** by running entirely within your local network. It leverages a server-side proxy architecture to bypass CORS limitations, allowing seamless communication with your local instances of the "Arr" suite, download clients, and media servers.

---

### Core Philosophy
* **Privacy-First:** Zero cloud telemetry. All service configurations and API keys are stored in a local, encrypted SQLite database.
* **Minimalist Utility:** A "soft grey" UI designed for high-density information without the visual clutter.
* **Configuration Flexibility:** Features an intelligent onboarding wizard and a persistent settings sidebar to scale with your home server as it grows.
* **Unified Health:** Real-time status monitoring (via pulsing health pips) for every connected service in your stack.

---

### The Tech Stack
| Layer | Technology |
| :--- | :--- |
| **Framework** | Next.js 14+ (App Router) |
| **Language** | TypeScript |
| **Local Database** | SQLite via Prisma ORM |
| **UI / UX** | Tailwind CSS + Shadcn/ui + Lucide Icons |
| **State Management** | Zustand |
| **Deployment** | Docker / Docker Compose |

---

### Feature Set
* **Service Aggregation:** Native support for **Sonarr, Radarr, Jellyseerr, Prowlarr, Emby, qBittorrent, Plex,** and **Jellyfin**.
* **Onboarding Wizard:** A guided setup process to discover and validate local service connections.
* **Modular Dashboard:** A widget-based three-pane layout featuring:
    * **Media Feed:** Upcoming air dates and recently added content.
    * **Transfer Monitor:** Active download progress and global speeds.
    * **Request Management:** Pending approval queues from Jellyseerr.
* **Settings Rail:** A persistent management interface for adding, removing, or reconfiguring services on the fly.

---

### Quick Start
```bash
# Clone the repository
git clone https://github.com/mguffin68/all-togetharr.git

# Spin up the local environment
docker-compose up -d
