"use client";

import { useMemo } from "react";
import { CodeSnippet } from "@/components/CodeSnippet";
import { API_BASE_URL, HAS_LIVE_BACKEND } from "@/lib/api";
import { useApiKey } from "@/lib/apiKey";
import { MOCK_API_KEY, mockAggregate, mockFinance, mockNews, mockWeather } from "@/lib/mock";
import { buildLanguageSnippets } from "@/lib/snippets";

type EndpointDoc = {
  id: string;
  method: "GET" | "POST";
  path: string;
  templatePath: string;
  summary: string;
  params: { name: string; in: "path" | "query"; type: string; required: boolean; description: string }[];
  example: () => unknown;
  callPath: string;
};

export default function DocsPage() {
  const { apiKey, hydrated } = useApiKey();

  const baseUrl = HAS_LIVE_BACKEND ? API_BASE_URL : "https://api.apiforge.dev";
  const keyForSnippets = hydrated ? apiKey : MOCK_API_KEY;

  const endpoints: EndpointDoc[] = useMemo(
    () => [
      {
        id: "weather",
        method: "GET",
        path: "/api/weather/{city}",
        templatePath: "/api/weather/{city}",
        summary:
          "Fetch current weather conditions for a city. Cached for 10 minutes per city (case-insensitive).",
        params: [
          {
            name: "city",
            in: "path",
            type: "string",
            required: true,
            description: "City name (e.g. Berlin, San Francisco).",
          },
        ],
        example: () => mockWeather("Berlin"),
        callPath: "/api/weather/Berlin",
      },
      {
        id: "news",
        method: "GET",
        path: "/api/news",
        templatePath: "/api/news?topic={topic}&limit={limit}",
        summary:
          "Search recent news articles by topic. Cached for 5 minutes per (topic, limit) pair.",
        params: [
          { name: "topic", in: "query", type: "string", required: true, description: "Search query (e.g. ai, climate)." },
          { name: "limit", in: "query", type: "integer", required: false, description: "Max articles to return (1-100, default 10)." },
        ],
        example: () => mockNews("ai", 3),
        callPath: "/api/news?topic=ai&limit=3",
      },
      {
        id: "finance",
        method: "GET",
        path: "/api/finance/quote",
        templatePath: "/api/finance/quote?symbol={symbol}",
        summary:
          "Current stock quote for a ticker symbol. Cached for 1 minute per symbol.",
        params: [
          { name: "symbol", in: "query", type: "string", required: true, description: "Stock ticker (e.g. AAPL, MSFT)." },
        ],
        example: () => mockFinance("AAPL"),
        callPath: "/api/finance/quote?symbol=AAPL",
      },
      {
        id: "aggregate",
        method: "GET",
        path: "/api/aggregate",
        templatePath: "/api/aggregate?city={city}&topic={topic}",
        summary:
          "Fan-out: call weather + news in parallel via asyncio.gather and combine the responses. Partial failures are returned in the errors object.",
        params: [
          { name: "city", in: "query", type: "string", required: true, description: "City for weather lookup." },
          { name: "topic", in: "query", type: "string", required: true, description: "Topic for news search." },
          { name: "limit", in: "query", type: "integer", required: false, description: "Max news articles (1-50, default 5)." },
        ],
        example: () => mockAggregate("Tokyo", "tech"),
        callPath: "/api/aggregate?city=Tokyo&topic=tech",
      },
    ],
    [],
  );

  const auth: EndpointDoc = {
    id: "register",
    method: "POST",
    path: "/auth/register",
    templatePath: "/auth/register",
    summary:
      "Create a developer account and receive a freshly minted API key prefixed with af_. Returned once — copy it immediately.",
    params: [
      { name: "email", in: "query", type: "string", required: true, description: "Developer email address (request body)." },
      { name: "password", in: "query", type: "string", required: true, description: "Password (min 8 characters)." },
    ],
    example: () => ({
      id: 42,
      email: "you@example.com",
      tier: "free",
      api_key: "af_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    }),
    callPath: "/auth/register",
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <header className="flex flex-col gap-2">
        <div className="section-title">Reference</div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-50">
          API documentation
        </h1>
        <p className="max-w-2xl text-sm text-slate-400">
          Base URL: <span className="mono text-slate-200">{baseUrl}</span> · All{" "}
          <span className="mono">/api/*</span> routes require an{" "}
          <span className="mono">X-API-Key</span> header.
        </p>
      </header>

      <div className="mt-8 grid gap-6 lg:grid-cols-[220px,1fr]">
        <aside className="hidden self-start lg:block">
          <nav className="panel sticky top-24 p-2 text-sm">
            <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Auth
            </div>
            <a
              href={`#${auth.id}`}
              className="block rounded-md px-3 py-1.5 text-slate-300 hover:bg-terminal-bg/60 hover:text-terminal-accent"
            >
              POST /auth/register
            </a>
            <div className="mt-2 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Gateway
            </div>
            {endpoints.map((e) => (
              <a
                key={e.id}
                href={`#${e.id}`}
                className="block rounded-md px-3 py-1.5 text-slate-300 hover:bg-terminal-bg/60 hover:text-terminal-accent"
              >
                {e.method} {e.path}
              </a>
            ))}
          </nav>
        </aside>

        <div className="space-y-12">
          <Section title="Authentication">
            <p className="text-sm text-slate-400">
              Every gateway request must include an{" "}
              <span className="mono">X-API-Key</span> header. Get a key via{" "}
              <span className="mono">/auth/register</span> or in the{" "}
              <a className="text-terminal-accent hover:underline" href="/dashboard">
                Dashboard
              </a>
              .
            </p>
            <EndpointBlock
              doc={auth}
              baseUrl={baseUrl}
              apiKey={keyForSnippets}
              isAuth
            />
          </Section>

          <Section title="Gateway endpoints">
            <p className="text-sm text-slate-400">
              All responses share consistent, predictable shapes. See each
              endpoint for its normalized schema and example payload.
            </p>
            <div className="space-y-10">
              {endpoints.map((doc) => (
                <EndpointBlock
                  key={doc.id}
                  doc={doc}
                  baseUrl={baseUrl}
                  apiKey={keyForSnippets}
                />
              ))}
            </div>
          </Section>

          <Section title="Rate limiting">
            <p className="text-sm text-slate-400">
              The free tier allows{" "}
              <span className="mono text-terminal-accent">100 req/hour</span>{" "}
              per API key. Every response includes:
            </p>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-300">
              <li>
                <span className="mono">X-RateLimit-Limit</span> — hourly limit
                for your tier
              </li>
              <li>
                <span className="mono">X-RateLimit-Remaining</span> — calls left
                in this hour
              </li>
              <li>
                <span className="mono">X-RateLimit-Reset</span> — seconds until
                the bucket rolls
              </li>
            </ul>
            <p className="mt-3 text-sm text-slate-400">
              When exceeded, the gateway returns{" "}
              <span className="mono">HTTP 429</span> with a JSON body containing{" "}
              <span className="mono">retry_after_seconds</span>.
            </p>
          </Section>

          <Section title="Errors">
            <div className="grid gap-3 sm:grid-cols-2">
              {[
                { code: 401, title: "Missing or invalid API key" },
                { code: 404, title: "Upstream resource not found" },
                { code: 429, title: "Rate limit exceeded" },
                { code: 502, title: "Upstream provider error" },
                { code: 503, title: "Provider API key not configured" },
                { code: 504, title: "Upstream timeout" },
              ].map((e) => (
                <div
                  key={e.code}
                  className="flex items-center gap-3 rounded-md border border-terminal-border bg-terminal-bg px-3 py-2 text-sm"
                >
                  <span className="badge mono bg-red-500/15 text-red-300">{e.code}</span>
                  <span className="text-slate-300">{e.title}</span>
                </div>
              ))}
            </div>
          </Section>
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="mb-4 text-xl font-semibold text-slate-100">{title}</h2>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

function EndpointBlock({
  doc,
  baseUrl,
  apiKey,
  isAuth = false,
}: {
  doc: {
    id: string;
    method: "GET" | "POST";
    path: string;
    templatePath: string;
    summary: string;
    params: { name: string; in: "path" | "query"; type: string; required: boolean; description: string }[];
    example: () => unknown;
    callPath: string;
  };
  baseUrl: string;
  apiKey: string;
  isAuth?: boolean;
}) {
  const example = useMemo(() => doc.example(), [doc]);
  const responseJson = useMemo(() => JSON.stringify(example, null, 2), [example]);

  const snippets = isAuth
    ? [
        {
          label: "curl",
          language: "shell" as const,
          code: `curl -s -X POST "${baseUrl}/auth/register" \\
  -H "Content-Type: application/json" \\
  -d '{"email":"you@example.com","password":"supersecret123"}'`,
        },
        {
          label: "Python",
          language: "python" as const,
          code: `import httpx

response = httpx.post(
    "${baseUrl}/auth/register",
    json={"email": "you@example.com", "password": "supersecret123"},
    timeout=10.0,
)
response.raise_for_status()
print(response.json()["api_key"])`,
        },
        {
          label: "JavaScript",
          language: "javascript" as const,
          code: `const res = await fetch("${baseUrl}/auth/register", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    email: "you@example.com",
    password: "supersecret123",
  }),
});
const { api_key } = await res.json();
console.log(api_key);`,
        },
      ]
    : buildLanguageSnippets({ baseUrl, apiKey, path: doc.callPath });

  return (
    <article id={doc.id} className="scroll-mt-24 panel">
      <header className="panel-header">
        <div className="flex items-center gap-3">
          <span
            className={`badge mono ${
              doc.method === "GET"
                ? "bg-emerald-500/15 text-emerald-300"
                : "bg-sky-500/15 text-sky-300"
            }`}
          >
            {doc.method}
          </span>
          <span className="mono text-sm text-slate-100">{doc.path}</span>
        </div>
      </header>
      <div className="space-y-5 px-4 py-4">
        <p className="text-sm text-slate-300">{doc.summary}</p>

        <div>
          <h4 className="section-title mb-2">Parameters</h4>
          {doc.params.length === 0 ? (
            <p className="text-sm text-slate-500">No parameters.</p>
          ) : (
            <div className="overflow-x-auto rounded-md border border-terminal-border">
              <table className="w-full text-left text-sm">
                <thead className="bg-terminal-bg/60 text-xs uppercase tracking-wider text-slate-400">
                  <tr>
                    <th className="px-3 py-2 font-semibold">Name</th>
                    <th className="px-3 py-2 font-semibold">In</th>
                    <th className="px-3 py-2 font-semibold">Type</th>
                    <th className="px-3 py-2 font-semibold">Required</th>
                    <th className="px-3 py-2 font-semibold">Description</th>
                  </tr>
                </thead>
                <tbody>
                  {doc.params.map((p) => (
                    <tr key={p.name} className="border-t border-terminal-border/60">
                      <td className="px-3 py-2 mono text-slate-100">{p.name}</td>
                      <td className="px-3 py-2 text-slate-400">{p.in}</td>
                      <td className="px-3 py-2 text-slate-400">{p.type}</td>
                      <td className="px-3 py-2">
                        {p.required ? (
                          <span className="badge bg-amber-500/15 text-amber-300">required</span>
                        ) : (
                          <span className="badge bg-slate-700/40 text-slate-300">optional</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-slate-300">{p.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <div>
            <h4 className="section-title mb-2">Request</h4>
            <CodeSnippet tabs={snippets} />
          </div>
          <div>
            <h4 className="section-title mb-2">Example response (200)</h4>
            <CodeSnippet
              tabs={[
                { label: "JSON", language: "json", code: responseJson },
              ]}
            />
          </div>
        </div>
      </div>
    </article>
  );
}
