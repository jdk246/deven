import { HomePage } from "../pages/HomePage";

const shellStyles = {
  page: {
    minHeight: "100vh",
    padding: "48px 24px",
  },
  container: {
    width: "min(960px, 100%)",
    margin: "0 auto",
  },
  hero: {
    display: "grid",
    gap: "12px",
    marginBottom: "32px",
  },
  eyebrow: {
    color: "#7dd3fc",
    fontSize: "0.875rem",
    textTransform: "uppercase" as const,
  },
  title: {
    margin: 0,
    fontSize: "clamp(2.5rem, 5vw, 4rem)",
  },
  subtitle: {
    margin: 0,
    maxWidth: "720px",
    color: "#bfd0e4",
    fontSize: "1.05rem",
  },
};

export function AppShell() {
  return (
    <main style={shellStyles.page}>
      <div style={shellStyles.container}>
        <header style={shellStyles.hero}>
          <div style={shellStyles.eyebrow}>trust-trace monorepo</div>
          <h1 style={shellStyles.title}>FastAPI + React scaffold is live.</h1>
          <p style={shellStyles.subtitle}>
            This chunk sets up the repo skeleton so we can start layering in
            market ingestion, scoring, and dashboard pages without fighting the
            project structure.
          </p>
        </header>
        <HomePage />
      </div>
    </main>
  );
}
