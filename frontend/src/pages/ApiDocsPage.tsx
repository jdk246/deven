import { useEffect, useState } from "react";
import {
  Bot,
  Braces,
  FileCode2,
  Globe,
  KeyRound,
  Server,
  ShieldAlert,
  Wrench,
} from "lucide-react";

import {
  fetchAgentExamples,
  fetchAgentTools,
  type AgentExampleItemResponse,
  type AgentToolDescriptorResponse,
} from "../api/trustTrace";
import { GlassCard } from "../components/GlassCard";
import { apiBaseUrl } from "../lib/env";

type ApiDocsPageProps = {
  agentMode: "deterministic" | "openai";
  dataMode: "seed" | "live";
  openaiReady: boolean;
};

type EndpointItem = {
  method: "GET" | "POST";
  path: string;
  title: string;
  description: string;
  audience: "Public" | "Admin";
};

const PUBLIC_ENDPOINTS: EndpointItem[] = [
  {
    method: "GET",
    path: "/health",
    title: "Backend health",
    description: "Basic service health check for uptime and connectivity.",
    audience: "Public",
  },
  {
    method: "GET",
    path: "/api/agent/health",
    title: "Agent status",
    description: "Returns current agent mode, data mode, and OpenAI readiness.",
    audience: "Public",
  },
  {
    method: "GET",
    path: "/api/tokens/trending",
    title: "Trending tokens",
    description: "Returns tracked tokens with attention score, liquidity, risk level, and chain metadata.",
    audience: "Public",
  },
  {
    method: "GET",
    path: "/api/tokens/{chain_id}/{contract_address}",
    title: "Token detail",
    description: "Returns token metadata, latest market snapshot, audits, smart-money signals, KOL mentions, and insight summary.",
    audience: "Public",
  },
  {
    method: "GET",
    path: "/api/kols",
    title: "KOL list",
    description: "Returns tracked KOL profiles and basic activity counts.",
    audience: "Public",
  },
  {
    method: "GET",
    path: "/api/kols/rankings",
    title: "KOL rankings",
    description: "Returns historical alignment rankings based on post-event performance.",
    audience: "Public",
  },
  {
    method: "GET",
    path: "/api/kols/{handle}",
    title: "KOL detail",
    description: "Returns one KOL profile with recent posts and extracted token mentions.",
    audience: "Public",
  },
  {
    method: "GET",
    path: "/api/kols/{handle}/track-record",
    title: "KOL track record",
    description: "Returns evaluated calls, pending calls, and the current track record score for one KOL.",
    audience: "Public",
  },
  {
    method: "GET",
    path: "/api/insights",
    title: "Token insights",
    description: "Returns deterministic token summaries and score breakdowns for tracked tokens.",
    audience: "Public",
  },
  {
    method: "GET",
    path: "/api/agent/tools",
    title: "Registered agent tools",
    description: "Lists the tool registry the backend agent can use.",
    audience: "Public",
  },
  {
    method: "GET",
    path: "/api/agent/examples",
    title: "Agent examples",
    description: "Returns backend-provided example prompts and expected response shapes.",
    audience: "Public",
  },
  {
    method: "POST",
    path: "/api/agent/query",
    title: "Agent query",
    description: "Ask the TrustTrace agent about tokens, KOLs, risks, rankings, and market context.",
    audience: "Public",
  },
];

const ADMIN_ENDPOINTS: EndpointItem[] = [
  {
    method: "GET",
    path: "/api/admin/validate",
    title: "Backend validation",
    description: "Returns demo-readiness checks for the local dataset and tool wiring.",
    audience: "Admin",
  },
  {
    method: "POST",
    path: "/api/admin/refresh",
    title: "Refresh jobs",
    description: "Runs ingestion and insight refresh jobs. Useful for demos, not meant as a public consumer endpoint.",
    audience: "Admin",
  },
  {
    method: "POST",
    path: "/api/admin/refresh-kol-performance",
    title: "Refresh KOL performance",
    description: "Recomputes KOL calls, evaluations, and track record scores.",
    audience: "Admin",
  },
];

function methodTone(method: "GET" | "POST") {
  return method === "GET"
    ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-300"
    : "bg-purple-500/15 border-purple-500/30 text-purple-300";
}

function SectionTitle({
  icon: Icon,
  title,
  subtitle,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="mb-4">
      <div className="flex items-center gap-2 mb-1">
        <Icon className="w-4 h-4 text-purple-300" />
        <h2 className="text-sm font-semibold text-white/85 uppercase tracking-wide">{title}</h2>
      </div>
      {subtitle ? <p className="text-sm text-white/55">{subtitle}</p> : null}
    </div>
  );
}

function CodeBlock({ children }: { children: string }) {
  return (
    <pre className="overflow-x-auto rounded-xl border border-white/10 bg-black/25 p-4 text-xs leading-6 text-white/80">
      <code>{children}</code>
    </pre>
  );
}

function EndpointList({ items }: { items: EndpointItem[] }) {
  return (
    <GlassCard>
      {items.map((item) => (
        <div
          key={`${item.method}:${item.path}`}
          className="border-b border-white/5 px-4 py-4 last:border-b-0 sm:px-5"
        >
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2 mb-1.5">
                <span
                  className={`rounded-lg border px-2 py-1 text-[11px] font-semibold uppercase tracking-wide ${methodTone(item.method)}`}
                >
                  {item.method}
                </span>
                <code className="text-sm text-white break-all">{item.path}</code>
              </div>
              <div className="text-sm font-semibold text-white">{item.title}</div>
              <p className="mt-1 text-sm text-white/60">{item.description}</p>
            </div>
            <span className="shrink-0 rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[11px] uppercase tracking-wide text-white/45">
              {item.audience}
            </span>
          </div>
        </div>
      ))}
    </GlassCard>
  );
}

export function ApiDocsPage({
  agentMode,
  dataMode,
  openaiReady,
}: ApiDocsPageProps) {
  const [tools, setTools] = useState<AgentToolDescriptorResponse[]>([]);
  const [examples, setExamples] = useState<AgentExampleItemResponse[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDocsData() {
      try {
        const [toolResponse, exampleResponse] = await Promise.all([
          fetchAgentTools(),
          fetchAgentExamples(),
        ]);

        if (!cancelled) {
          setTools(toolResponse.items);
          setExamples(exampleResponse.items);
          setLoadError(null);
        }
      } catch (caughtError) {
        if (!cancelled) {
          setLoadError(
            caughtError instanceof Error
              ? caughtError.message
              : "Failed to load live API docs metadata.",
          );
        }
      }
    }

    void loadDocsData();
    return () => {
      cancelled = true;
    };
  }, []);

  const quickStartCurl = `curl ${apiBaseUrl}/api/tokens/trending?limit=5`;
  const quickStartAgent = `curl -X POST ${apiBaseUrl}/api/agent/query \\
  -H "Content-Type: application/json" \\
  -d '{
    "message": "Which KOLs have the best track record?",
    "debug": true
  }'`;
  const quickStartJs = `const response = await fetch("${apiBaseUrl}/api/agent/query", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    message: "Why is this token trending?",
    chain_id: "56",
    debug: true,
  }),
});

const data = await response.json();`;

  return (
    <div className="min-h-screen text-white relative z-10">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-10">
        <div className="mb-8">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold mb-2 bg-gradient-to-r from-white to-purple-200 bg-clip-text text-transparent">
            API Documentation
          </h1>
          <p className="text-sm sm:text-base text-white/60 max-w-3xl">
            This page documents the TrustTrace backend API for external consumers and demo partners.
            In the current build, the API surface is callable without authentication if you expose the
            backend publicly, but it is still a demo-grade interface and not yet production-hardened.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
          <GlassCard className="p-4 sm:p-5">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs text-white/60 uppercase tracking-wide">Base URL</div>
              <Globe className="w-4 h-4 text-purple-300" />
            </div>
            <div className="text-sm font-semibold text-white break-all">{apiBaseUrl}</div>
            <div className="text-xs text-white/45 mt-2">Use your deployed backend URL in production.</div>
          </GlassCard>

          <GlassCard className="p-4 sm:p-5">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs text-white/60 uppercase tracking-wide">Access</div>
              <KeyRound className="w-4 h-4 text-amber-300" />
            </div>
            <div className="text-sm font-semibold text-white">No auth in demo build</div>
            <div className="text-xs text-white/45 mt-2">No API key, auth layer, or rate limiting is enforced yet.</div>
          </GlassCard>

          <GlassCard className="p-4 sm:p-5">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs text-white/60 uppercase tracking-wide">Agent Mode</div>
              <Bot className="w-4 h-4 text-cyan-300" />
            </div>
            <div className="text-sm font-semibold text-white capitalize">{agentMode}</div>
            <div className="text-xs text-white/45 mt-2">
              OpenAI ready: {openaiReady ? "yes" : "no"} | Data mode: {dataMode}
            </div>
          </GlassCard>

          <GlassCard className="p-4 sm:p-5">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs text-white/60 uppercase tracking-wide">Stability</div>
              <ShieldAlert className="w-4 h-4 text-rose-300" />
            </div>
            <div className="text-sm font-semibold text-white">Public demo surface</div>
            <div className="text-xs text-white/45 mt-2">
              Good for demos and integrations, but still missing auth, quotas, and versioning guarantees.
            </div>
          </GlassCard>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-8">
          <div>
            <SectionTitle
              icon={Braces}
              title="Quick Start"
              subtitle="These are the fastest ways to hit the API from curl or JavaScript."
            />
            <div className="space-y-4">
              <GlassCard className="p-4 sm:p-5">
                <div className="text-sm font-semibold text-white mb-3">Trending tokens</div>
                <CodeBlock>{quickStartCurl}</CodeBlock>
              </GlassCard>
              <GlassCard className="p-4 sm:p-5">
                <div className="text-sm font-semibold text-white mb-3">Agent query</div>
                <CodeBlock>{quickStartAgent}</CodeBlock>
              </GlassCard>
              <GlassCard className="p-4 sm:p-5">
                <div className="text-sm font-semibold text-white mb-3">JavaScript fetch example</div>
                <CodeBlock>{quickStartJs}</CodeBlock>
              </GlassCard>
            </div>
          </div>

          <div>
            <SectionTitle
              icon={Server}
              title="Usage Notes"
              subtitle="Important behavior to know before you point external users at the API."
            />
            <GlassCard className="p-4 sm:p-5">
              <div className="space-y-3 text-sm text-white/65">
                <p>
                  All endpoints return JSON. The current response shapes are stable enough for the demo,
                  but the project does not yet implement versioned APIs.
                </p>
                <p>
                  Public consumer endpoints are the market, KOL, insight, and agent routes. Admin routes
                  exist for refresh and validation workflows and should be treated as operational endpoints.
                </p>
                <p>
                  If you deploy the backend openly right now, the API is effectively public because there
                  is no auth or rate limiting layer in front of it yet.
                </p>
                <p>
                  The most complete written contract still lives in{" "}
                  <code className="text-white/85">backend/API_CONTRACT.md</code>, and this page is the
                  website-friendly view of that surface.
                </p>
              </div>
            </GlassCard>
          </div>
        </div>

        <div className="mb-8">
          <SectionTitle
            icon={FileCode2}
            title="Public Endpoints"
            subtitle="These are the endpoints external consumers are most likely to use."
          />
          <EndpointList items={PUBLIC_ENDPOINTS} />
        </div>

        <div className="mb-8">
          <SectionTitle
            icon={ShieldAlert}
            title="Admin Endpoints"
            subtitle="Useful for local demos and refresh workflows, but not the primary public consumer surface."
          />
          <EndpointList items={ADMIN_ENDPOINTS} />
        </div>

        <div className="mb-8">
          <SectionTitle
            icon={Wrench}
            title="Agent Tools"
            subtitle="Live tool registry returned by the backend. This is what the agent can currently use."
          />
          <GlassCard>
            {tools.length > 0 ? (
              tools.map((tool) => (
                <div
                  key={tool.name}
                  className="border-b border-white/5 px-4 py-4 last:border-b-0 sm:px-5"
                >
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-white">{tool.name}</div>
                      <p className="mt-1 text-sm text-white/60">{tool.description}</p>
                    </div>
                    <span className="shrink-0 rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[11px] uppercase tracking-wide text-white/45">
                      {tool.category}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="px-4 py-5 text-sm text-white/60 sm:px-5">
                {loadError ?? "Loading live tool registry..."}
              </div>
            )}
          </GlassCard>
        </div>

        <div>
          <SectionTitle
            icon={Bot}
            title="Backend Examples"
            subtitle="Live examples returned by the backend for the agent API."
          />
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            {examples.length > 0 ? (
              examples.map((example) => (
                <GlassCard key={example.title} className="p-4 sm:p-5">
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <span
                      className={`rounded-lg border px-2 py-1 text-[11px] font-semibold uppercase tracking-wide ${methodTone(example.method)}`}
                    >
                      {example.method}
                    </span>
                    <code className="text-xs text-white/70 break-all">{example.endpoint}</code>
                  </div>
                  <div className="text-sm font-semibold text-white mb-1.5">{example.title}</div>
                  <p className="text-sm text-white/60 mb-4">{example.description}</p>
                  {example.request_body ? (
                    <div className="mb-4">
                      <div className="text-xs uppercase tracking-wide text-white/45 mb-2">Request body</div>
                      <CodeBlock>{JSON.stringify(example.request_body, null, 2)}</CodeBlock>
                    </div>
                  ) : null}
                  <div>
                    <div className="text-xs uppercase tracking-wide text-white/45 mb-2">Expected response shape</div>
                    <CodeBlock>{JSON.stringify(example.expected_response_shape, null, 2)}</CodeBlock>
                  </div>
                </GlassCard>
              ))
            ) : (
              <GlassCard className="p-4 sm:p-5">
                <div className="text-sm text-white/60">
                  {loadError ?? "Loading backend-provided examples..."}
                </div>
              </GlassCard>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
