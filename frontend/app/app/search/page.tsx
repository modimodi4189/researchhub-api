import { AppShell } from "@/components/app/app-shell";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { SemanticSearch } from "@/components/search/semantic-search";

export default function SearchPage() {
  return (
    <ProtectedRoute>
      <AppShell
        activeNavigation="Search"
        title="Search"
        subtitle="Semantic search across your papers and public papers."
      >
        <SemanticSearch />
      </AppShell>
    </ProtectedRoute>
  );
}
