import Link from "next/link";

export function Logo({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const dim =
    size === "sm" ? "h-7 w-7 text-sm" : size === "lg" ? "h-12 w-12 text-xl" : "h-9 w-9 text-base";
  return (
    <Link href="/" className="group flex items-center gap-2.5">
      <span
        className={`${dim} grid place-items-center rounded-md border border-terminal-border bg-terminal-panel font-mono font-bold text-terminal-accent shadow-glow transition group-hover:border-terminal-accent/60`}
        aria-hidden
      >
        ⌁
      </span>
      <span className="font-mono text-base font-semibold tracking-tight text-slate-100">
        api<span className="text-terminal-accent">forge</span>
      </span>
    </Link>
  );
}
