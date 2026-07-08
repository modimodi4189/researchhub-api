import {
  Archive,
  Bell,
  BookOpen,
  Compass,
  FileText,
  FolderKanban,
  Library,
  Search,
  Settings,
  Sparkles,
} from "lucide-react";
import { ApiHealthStatus } from "@/components/api-health-status";

const navigation = [
  { name: "Library", icon: Library, active: true },
  { name: "Search", icon: Search },
  { name: "Collections", icon: FolderKanban },
  { name: "Public Papers", icon: Compass },
  { name: "Settings", icon: Settings },
];

const sections = [
  {
    title: "Library",
    description: "A quiet home for saved papers, reading states, and notes.",
    icon: BookOpen,
    meta: "Personal workspace",
    items: ["Recent papers", "Reading queue", "Annotations"],
  },
  {
    title: "Search",
    description: "A focused area for semantic discovery and filtered queries.",
    icon: Search,
    meta: "Discovery",
    items: ["Query input", "Filters", "Result preview"],
  },
  {
    title: "Collections",
    description: "A structured view for grouped papers and research themes.",
    icon: Archive,
    meta: "Organization",
    items: ["Collection list", "Shared themes", "Pinned groups"],
  },
  {
    title: "Public Papers",
    description: "A browsing surface for published and community-visible papers.",
    icon: FileText,
    meta: "Public catalog",
    items: ["Browse feed", "Topic chips", "Paper summaries"],
  },
  {
    title: "Settings",
    description: "A simple preferences area for workspace and account controls later.",
    icon: Settings,
    meta: "Preferences",
    items: ["Profile shell", "Display options", "Import defaults"],
  },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-canvas text-ink">
      <div className="grid min-h-screen grid-cols-[264px_1fr]">
        <aside className="border-r border-border bg-sidebar px-4 py-5">
          <div className="mb-8 flex items-center gap-3 px-2">
            <div className="flex size-10 items-center justify-center rounded-md border border-border bg-surface text-primary">
              <Sparkles className="size-5" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-semibold tracking-tight">ResearchHub</p>
              <p className="text-xs text-muted-foreground">Research workspace</p>
            </div>
          </div>

          <nav aria-label="Primary navigation" className="space-y-1">
            {navigation.map((item) => (
              <a
                key={item.name}
                href={`#${item.name.toLowerCase().replaceAll(" ", "-")}`}
                className={`flex items-center gap-3 rounded-md px-3 py-2.5 text-sm transition ${
                  item.active
                    ? "bg-sidebar-accent text-sidebar-accent-foreground shadow-sm"
                    : "text-muted-foreground hover:bg-sidebar-accent/70 hover:text-foreground"
                }`}
              >
                <item.icon className="size-4" aria-hidden="true" />
                <span>{item.name}</span>
              </a>
            ))}
          </nav>

          <div className="mt-8 rounded-md border border-border bg-surface/70 p-3">
            <p className="text-xs font-medium text-foreground">Shell milestone</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              Static layout only. Backend, auth, and real paper cards stay out
              of this pass.
            </p>
          </div>
        </aside>

        <section className="flex min-w-0 flex-col">
          <header className="flex h-16 items-center justify-between border-b border-border bg-background/80 px-7">
            <div>
              <p className="text-sm font-medium">Library</p>
              <p className="text-xs text-muted-foreground">
                Inspecting spacing, hierarchy, and navigation rhythm.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <ApiHealthStatus />
              <button
                type="button"
                className="flex size-9 items-center justify-center rounded-md border border-border bg-surface text-muted-foreground hover:text-foreground"
                aria-label="Notifications"
              >
                <Bell className="size-4" aria-hidden="true" />
              </button>
              <div className="flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-1.5">
                <div className="size-6 rounded bg-primary-subtle" />
                <span className="text-xs font-medium">Local preview</span>
              </div>
            </div>
          </header>

          <div className="flex-1 overflow-auto px-7 py-6">
            <div className="mx-auto max-w-6xl">
              <section className="mb-6 rounded-md border border-border bg-surface px-6 py-5">
                <div className="flex items-start justify-between gap-6">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
                      First visible structure
                    </p>
                    <h1 className="mt-3 text-2xl font-semibold tracking-tight">
                      Desktop app shell for focused research work
                    </h1>
                    <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                      This pass establishes the navigation frame, top bar, and
                      placeholder content zones before real paper workflows are
                      introduced.
                    </p>
                  </div>
                  <div className="hidden rounded-md border border-border bg-muted px-4 py-3 text-right md:block">
                    <p className="text-xs text-muted-foreground">Mode</p>
                    <p className="text-sm font-medium">Static preview</p>
                  </div>
                </div>
              </section>

              <div className="grid grid-cols-2 gap-4">
                {sections.map((section) => (
                  <section
                    key={section.title}
                    id={section.title.toLowerCase().replaceAll(" ", "-")}
                    className="min-h-56 rounded-md border border-border bg-card p-5"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-center gap-3">
                        <div className="flex size-10 items-center justify-center rounded-md bg-muted text-primary">
                          <section.icon className="size-5" aria-hidden="true" />
                        </div>
                        <div>
                          <h2 className="text-base font-semibold">
                            {section.title}
                          </h2>
                          <p className="text-xs text-muted-foreground">
                            {section.meta}
                          </p>
                        </div>
                      </div>
                    </div>

                    <p className="mt-4 text-sm leading-6 text-muted-foreground">
                      {section.description}
                    </p>

                    <div className="mt-5 space-y-2">
                      {section.items.map((item) => (
                        <div
                          key={item}
                          className="flex items-center justify-between rounded-md border border-border bg-background px-3 py-2"
                        >
                          <span className="text-sm">{item}</span>
                          <span className="h-2 w-16 rounded-full bg-muted" />
                        </div>
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
