import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  Cloud,
  Code2,
  Gauge,
  Newspaper,
  ShieldCheck,
  TrendingUp,
  Zap,
} from "lucide-react";
import { CodeSnippet } from "@/components/CodeSnippet";

const TIERS = [
  {
    name: "Free",
    price: "$0",
    cadence: "/ forever",
    quota: "100 requests / hour",
    description: "For prototypes, indie hacks, and learning.",
    features: [
      "All gateway endpoints",
      "10-minute weather cache",
      "Basic usage analytics",
      "1 API key",
    ],
    cta: { label: "Start free", href: "/dashboard", primary: true },
    accent: false,
  },
  {
    name: "Pro",
    price: "$29",
    cadence: "/ month",
    quota: "1,000 requests / hour",
    description: "For production traffic and growing apps.",
    features: [
      "Everything in Free",
      "Priority upstream connections",
      "Advanced analytics + CSV export",
      "5 API keys + key rotation",
      "Email support",
    ],
    cta: { label: "Upgrade", href: "/dashboard", primary: true },
    accent: true,
  },
];

const FEATURES = [
  {
    icon: Zap,
    title: "One key, three providers",
    body: "Hit OpenWeather, NewsAPI, and Alpha Vantage through one base URL and one API key. No more juggling SDKs.",
  },
  {
    icon: ShieldCheck,
    title: "Built-in rate limiting",
    body: "Redis-backed hourly buckets, tier-aware limits, and X-RateLimit-* headers on every response.",
  },
  {
    icon: BarChart3,
    title: "Usage analytics",
    body: "Every call is logged with latency, status, and upstream timing. Visualize the whole funnel in /analytics.",
  },
  {
    icon: Gauge,
    title: "Smart caching",
    body: "Sensible per-endpoint TTLs (weather 10m, news 5m, finance 1m) cut your upstream bill without stale data.",
  },
];

export default function LandingPage() {
  return (
    <div className="grid-bg">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="mx-auto max-w-7xl px-4 pb-20 pt-16 sm:px-6 sm:pt-24">
          <div className="mx-auto max-w-3xl text-center">
            <span className="inline-flex items-center gap-2 rounded-full border border-terminal-border bg-terminal-panel/60 px-3 py-1 text-xs text-slate-300">
              <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-terminal-accent" />
              <span className="mono">v0.1</span>
              <span className="text-slate-500">/</span>
              <span>Public beta — free tier live</span>
            </span>
            <h1 className="mt-6 text-balance text-4xl font-bold tracking-tight text-slate-50 sm:text-6xl">
              One gateway for the APIs you{" "}
              <span className="bg-gradient-to-r from-terminal-accent to-emerald-200 bg-clip-text text-transparent">
                actually ship with
              </span>
              .
            </h1>
            <p className="mt-5 text-balance text-base text-slate-300 sm:text-lg">
              APIForge unifies weather, news, and finance providers behind a
              single rate-limited REST endpoint — with analytics, caching, and
              authentication baked in.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <Link href="/dashboard" className="btn-primary">
                Get an API key
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="/docs" className="btn-ghost">
                <Code2 className="h-4 w-4" />
                Read the docs
              </Link>
            </div>
            <p className="mt-3 text-xs text-slate-500">
              No credit card. 100 requests/hour free, forever.
            </p>
          </div>

          {/* Hero terminal */}
          <div className="mx-auto mt-14 max-w-3xl">
            <CodeSnippet
              title="Try it"
              tabs={[
                {
                  label: "curl",
                  language: "shell",
                  code: `# Register, get an API key, make a call.
curl -s -X POST https://api.apiforge.dev/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{"email":"you@example.com","password":"supersecret123"}'

curl -s "https://api.apiforge.dev/api/weather/Berlin" \\
  -H "X-API-Key: af_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" | jq`,
                },
                {
                  label: "Python",
                  language: "python",
                  code: `import httpx

api_key = "af_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
weather = httpx.get(
    "https://api.apiforge.dev/api/weather/Berlin",
    headers={"X-API-Key": api_key},
).json()

print(weather["temperature_c"], weather["condition"])`,
                },
                {
                  label: "JavaScript",
                  language: "javascript",
                  code: `const apiKey = "af_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx";
const res = await fetch("https://api.apiforge.dev/api/weather/Berlin", {
  headers: { "X-API-Key": apiKey },
});
const weather = await res.json();
console.log(weather.temperature_c, weather.condition);`,
                },
              ]}
            />
          </div>
        </div>
      </section>

      {/* Endpoint pills */}
      <section className="border-y border-terminal-border bg-terminal-panel/30">
        <div className="mx-auto grid max-w-7xl gap-4 px-4 py-10 sm:grid-cols-2 sm:px-6 lg:grid-cols-4">
          {[
            { icon: Cloud, label: "Weather", path: "/api/weather/{city}" },
            { icon: Newspaper, label: "News", path: "/api/news?topic=..." },
            { icon: TrendingUp, label: "Finance", path: "/api/finance/quote" },
            { icon: Zap, label: "Aggregate", path: "/api/aggregate?city=..." },
          ].map(({ icon: Icon, label, path }) => (
            <div
              key={label}
              className="flex items-center gap-3 rounded-lg border border-terminal-border bg-terminal-bg px-4 py-3"
            >
              <Icon className="h-5 w-5 text-terminal-accent" />
              <div>
                <div className="text-sm font-semibold text-slate-100">{label}</div>
                <div className="mono text-xs text-slate-400">{path}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <div className="section-title">Why APIForge</div>
          <h2 className="mt-3 text-3xl font-bold tracking-tight text-slate-50 sm:text-4xl">
            Production plumbing, on tap.
          </h2>
          <p className="mt-3 text-slate-400">
            Auth, rate limiting, caching, analytics. The boring-but-critical
            scaffolding you&apos;d otherwise build for every project.
          </p>
        </div>
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map(({ icon: Icon, title, body }) => (
            <div key={title} className="panel p-5">
              <div className="flex h-9 w-9 items-center justify-center rounded-md border border-terminal-border bg-terminal-bg text-terminal-accent">
                <Icon className="h-5 w-5" />
              </div>
              <h3 className="mt-4 text-base font-semibold text-slate-100">{title}</h3>
              <p className="mt-1.5 text-sm text-slate-400">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="border-t border-terminal-border bg-terminal-panel/30">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6">
          <div className="mx-auto max-w-2xl text-center">
            <div className="section-title">Pricing</div>
            <h2 className="mt-3 text-3xl font-bold tracking-tight text-slate-50 sm:text-4xl">
              Pay for traffic, not seats.
            </h2>
            <p className="mt-3 text-slate-400">
              Start free, upgrade when your app finds its audience.
            </p>
          </div>

          <div className="mx-auto mt-12 grid max-w-4xl gap-6 sm:grid-cols-2">
            {TIERS.map((tier) => (
              <div
                key={tier.name}
                className={`panel p-6 ${
                  tier.accent ? "border-terminal-accent/50 shadow-glow" : ""
                }`}
              >
                <div className="flex items-baseline justify-between">
                  <h3 className="text-lg font-semibold text-slate-100">{tier.name}</h3>
                  {tier.accent && (
                    <span className="badge bg-terminal-accentDim/40 text-terminal-accent">
                      Most popular
                    </span>
                  )}
                </div>
                <div className="mt-3 flex items-baseline gap-1">
                  <span className="text-4xl font-bold text-slate-50">{tier.price}</span>
                  <span className="text-sm text-slate-400">{tier.cadence}</span>
                </div>
                <div className="mt-2 mono text-sm text-terminal-accent">{tier.quota}</div>
                <p className="mt-3 text-sm text-slate-400">{tier.description}</p>
                <ul className="mt-5 space-y-2 text-sm text-slate-200">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2">
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-terminal-accent" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
                <Link
                  href={tier.cta.href}
                  className={`mt-6 w-full ${
                    tier.cta.primary ? "btn-primary" : "btn-ghost"
                  }`}
                >
                  {tier.cta.label}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="mx-auto max-w-3xl px-4 py-20 text-center sm:px-6">
        <h2 className="text-3xl font-bold text-slate-50 sm:text-4xl">
          Ship the integration in an hour, not a sprint.
        </h2>
        <p className="mt-3 text-slate-400">
          Sign up, grab a key, and you&apos;ll be making normalized API calls in
          your terminal in under five minutes.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Link href="/dashboard" className="btn-primary">
            Get your API key
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link href="/explorer" className="btn-ghost">
            Try the explorer
          </Link>
        </div>
      </section>
    </div>
  );
}
