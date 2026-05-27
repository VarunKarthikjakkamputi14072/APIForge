"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "./Logo";
import { Github } from "lucide-react";

const NAV_LINKS: { href: string; label: string }[] = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/explorer", label: "Explorer" },
  { href: "/analytics", label: "Analytics" },
  { href: "/docs", label: "Docs" },
];

function isActive(pathname: string | null, href: string): boolean {
  if (!pathname) return false;
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Navbar() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-40 border-b border-terminal-border bg-terminal-bg/85 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        <div className="flex items-center gap-8">
          <Logo />
          <nav className="hidden items-center gap-1 md:flex">
            {NAV_LINKS.map((link) => {
              const active = isActive(pathname, link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
                    active
                      ? "bg-terminal-panel text-terminal-accent"
                      : "text-slate-300 hover:bg-terminal-panel/60 hover:text-slate-100"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="flex items-center gap-2">
          <a
            href="https://github.com/VarunKarthikjakkamputi14072/APIForge-"
            target="_blank"
            rel="noreferrer"
            className="btn-ghost hidden sm:inline-flex"
          >
            <Github className="h-4 w-4" />
            <span>GitHub</span>
          </a>
          <Link href="/dashboard" className="btn-primary">
            Console
          </Link>
        </div>
      </div>
      {/* Mobile nav */}
      <nav className="flex items-center gap-1 overflow-x-auto border-t border-terminal-border px-4 py-2 md:hidden">
        {NAV_LINKS.map((link) => {
          const active = isActive(pathname, link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition ${
                active
                  ? "bg-terminal-panel text-terminal-accent"
                  : "text-slate-300 hover:text-slate-100"
              }`}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
