from typing import TypedDict

from stackops.utils.schemas.installer.installer_types import InstallerCategoryLabel


class InstallerCategoryDefinition(TypedDict):
    title: str
    description: str


def installer_category_definition(label: InstallerCategoryLabel) -> InstallerCategoryDefinition:
    match label:
        case "system-setup":
            return InstallerCategoryDefinition(
                title="System Setup & Package Management",
                description="Bootstrap installers, package managers, updaters, system prerequisites, and platform setup helpers.",
            )
        case "languages-runtimes":
            return InstallerCategoryDefinition(
                title="Languages & Runtimes",
                description="Programming language runtimes, toolchains, language servers, kernels, and runtime managers.",
            )
        case "editors-ides":
            return InstallerCategoryDefinition(
                title="Editors & IDEs",
                description="Graphical and terminal editors, coding IDEs, and editor-oriented installation helpers.",
            )
        case "version-control":
            return InstallerCategoryDefinition(
                title="Version Control",
                description="Git, GitHub, worktree, repository inspection, and Git terminal UI tooling.",
            )
        case "build-devops-containers":
            return InstallerCategoryDefinition(
                title="Build, DevOps & Containers",
                description="Build helpers, development containers, container tooling, service orchestration, and infrastructure utilities.",
            )
        case "ai-agents-assistants":
            return InstallerCategoryDefinition(
                title="AI Agents & Assistants",
                description="AI coding agents, chat CLIs, agent launchers, MCP tooling, and assistant-oriented apps.",
            )
        case "terminals-shells":
            return InstallerCategoryDefinition(
                title="Terminals & Shells",
                description="Terminal emulators, shells, prompt engines, shell history tools, fonts, and terminal UX helpers.",
            )
        case "terminal-workspaces":
            return InstallerCategoryDefinition(
                title="Terminal Workspaces & Multiplexers",
                description="Terminal multiplexers, workspace managers, web terminals, shared terminal sessions, and process panes.",
            )
        case "search-navigation":
            return InstallerCategoryDefinition(
                title="Search & Navigation",
                description="File, code, document, shell-history, semantic, and fuzzy-search tools.",
            )
        case "file-managers":
            return InstallerCategoryDefinition(
                title="File Managers & Directory Browsers",
                description="Terminal and web file managers, directory browsers, ls replacements, and remote file browsing tools.",
            )
        case "file-operations-archives":
            return InstallerCategoryDefinition(
                title="File Operations & Archives",
                description="Archiving, copying, removal, file identification, previewing, cleanup, and clipboard utilities.",
            )
        case "storage-backup-sync":
            return InstallerCategoryDefinition(
                title="Storage, Backup & Sync",
                description="Disk usage analyzers, cloud sync, backup tools, filesystem integrations, and continuous synchronization.",
            )
        case "data-format-tools":
            return InstallerCategoryDefinition(
                title="Data & Format Tools",
                description="Structured data viewers, processors, converters, and command-line table or markup utilities.",
            )
        case "databases":
            return InstallerCategoryDefinition(
                title="Databases & SQL Clients",
                description="Database engines, database CLIs, SQL clients, database browsers, and TUI database visualizers.",
            )
        case "networking-diagnostics":
            return InstallerCategoryDefinition(
                title="Networking & Diagnostics",
                description="Network monitors, scanners, diagnostics, VPN clients, firewalls, IP lookup, and traffic inspection tools.",
            )
        case "tunnels-remote-access":
            return InstallerCategoryDefinition(
                title="Tunnels & Remote Access",
                description="Localhost tunnels, reverse proxies, remote desktop tools, remote shells, and browser-based terminal access.",
            )
        case "file-transfer-sharing":
            return InstallerCategoryDefinition(
                title="File Transfer & Sharing",
                description="Direct file transfer, encrypted sharing, local file servers, QR-based transfer, torrents, and shareable folders.",
            )
        case "cloud-saas":
            return InstallerCategoryDefinition(
                title="Cloud & SaaS CLIs",
                description="Cloud provider, SaaS administration, cloud storage, and Cloudflare tools.",
            )
        case "browsers-web-access":
            return InstallerCategoryDefinition(
                title="Browsers & Web Access",
                description="Desktop browsers, terminal browsers, browser helpers, browser automation, and web access utilities.",
            )
        case "web-scraping-conversion":
            return InstallerCategoryDefinition(
                title="Web Scraping & Content Conversion",
                description="Website crawling, scraping, document extraction, HTML conversion, and web-to-text workflows.",
            )
        case "documents-markdown-latex":
            return InstallerCategoryDefinition(
                title="Documents, Markdown & LaTeX",
                description="Markdown renderers, document converters, PDF helpers, LaTeX distributions, editors, and presentation-from-text tools.",
            )
        case "graphics-images-ocr-diagrams":
            return InstallerCategoryDefinition(
                title="Graphics, Images, OCR & Diagrams",
                description="Image manipulation, terminal graphics, OCR, PDF/SVG rendering, diagrams, and graph visualization.",
            )
        case "media-audio-video":
            return InstallerCategoryDefinition(
                title="Media, Audio & Video",
                description="Music players, media downloaders, video tools, streaming apps, recording apps, and conferencing clients.",
            )
        case "presentations-recording":
            return InstallerCategoryDefinition(
                title="Presentations & Recording",
                description="Presentation tools, screen annotation, terminal recording, streaming helpers, and diagramming for talks.",
            )
        case "productivity-knowledge":
            return InstallerCategoryDefinition(
                title="Productivity & Knowledge",
                description="Notes, cheatsheets, text expansion, timers, prompt helpers, and productivity-oriented CLI utilities.",
            )
        case "security-credentials-privacy":
            return InstallerCategoryDefinition(
                title="Security, Credentials & Privacy",
                description="Password managers, encryption, one-time secrets, VPN clients, firewall helpers, and privacy-oriented tools.",
            )
        case "monitoring-performance":
            return InstallerCategoryDefinition(
                title="Monitoring, Performance & System Info",
                description="System monitors, process viewers, resource profilers, benchmarking tools, log analyzers, and system info displays.",
            )
        case "qr-mobile-device-tools":
            return InstallerCategoryDefinition(
                title="QR, Mobile & Device Tools",
                description="QR code utilities, Android mirroring, mobile transfer helpers, Wi-Fi sharing, and multi-device control.",
            )
        case "terminal-fun-visuals":
            return InstallerCategoryDefinition(
                title="Terminal Fun & Visuals",
                description="ASCII art, terminal color effects, decorative terminal output, terminal graphics, and visual demos.",
            )
        case "email-communications":
            return InstallerCategoryDefinition(
                title="Email & Communications",
                description="Email clients, video conferencing, and communication-focused desktop or terminal tools.",
            )
        case "finance-markets":
            return InstallerCategoryDefinition(
                title="Finance & Markets",
                description="Market, crypto, and prediction-market tools.",
            )
        case "windows-platform":
            return InstallerCategoryDefinition(
                title="Windows Platform Tools",
                description="Windows-specific package managers, PowerShell tools, Visual Studio prerequisites, filesystem helpers, X11, and Windows desktop utilities.",
            )
