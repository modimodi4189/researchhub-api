import { AppShell } from "@/components/app/app-shell";
import { ProtectedRoute } from "@/components/auth/protected-route";

export default function AppPage() {
  return (
    <ProtectedRoute>
      <AppShell />
    </ProtectedRoute>
  );
}
