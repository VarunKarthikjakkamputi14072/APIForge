import Link from "next/link";
import { Logo } from "./Logo";

export function Footer() {
  return (
    <footer className="border-t border-terminal-border bg-terminal-bg/80">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 sm:px-6 md:grid-cols-4">
        <div className="md:col-span-2">
          <Logo />
          <p className="mt-3 max-w-sm text-sm text-slate-400">
            APIForge unifies third-party APIs behind a single, rate-limited,
            analytics-rich endpoint. Built for indie developers and ship-fast
            teams.
          </p>
        </div>
        <div>
          <div className="section-title mb-3">Product</div>
          <ul className="space-y-2 text-sm text-slate-300">
            <li>
              <Link href="/dashboard" className="hover:text-terminal-accent">
                Dashboard
              </Link>
            </li>
            <li>
              <Link href="/explorer" className="hover:text-terminal-accent">
                API Explorer
              </Link>
            </li>
            <li>
              <Link href="/analytics" className="hover:text-terminal-accent">
                Analytics
              </Link>
            </li>
          </ul>
        </div>
        <div>
          <div className="section-title mb-3">Developers</div>
          <ul className="space-y-2 text-sm text-slate-300">
            <li>
              <Link href="/docs" className="hover:text-terminal-accent">
                Documentation
              </Link>
            </li>
            <li>
              <a
                href="https://github.com/VarunKarthikjakkamputi14072/APIForge-"
                className="hover:text-terminal-accent"
                target="_blank"
                rel="noreferrer"
              >
                GitHub
              </a>
            </li>
          </ul>
        </div>
      </div>
      <div className="border-t border-terminal-border px-4 py-4 text-center text-xs text-slate-500 sm:px-6">
        <span className="mono">apiforge</span> · MIT licensed · built with
        FastAPI + Next.js
      </div>
    </footer>
  );
}
