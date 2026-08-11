import { AppShell } from "@/components/app/app-shell";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { CollectionsManager } from "@/components/collections/collections-manager";

export default function CollectionsPage() {
  return (
    <ProtectedRoute>
      <AppShell
        activeNavigation="Collections"
        title="Collections"
        subtitle="Manage saved paper collections from the backend API."
      >
        <CollectionsManager />
      </AppShell>
    </ProtectedRoute>
  );
}
