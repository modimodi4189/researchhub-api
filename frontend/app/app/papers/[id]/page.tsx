import { AppShell } from "@/components/app/app-shell";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { PaperDetail } from "@/components/papers/paper-detail";

type PaperDetailPageProps = {
  params: Promise<{
    id: string;
  }>;
};

export default async function PaperDetailPage({ params }: PaperDetailPageProps) {
  const { id } = await params;

  return (
    <ProtectedRoute>
      <AppShell
        title="Paper Detail"
        subtitle="Full paper record loaded from the backend API."
      >
        <PaperDetail paperId={id} />
      </AppShell>
    </ProtectedRoute>
  );
}
