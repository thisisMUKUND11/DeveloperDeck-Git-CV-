import { AUTHOR, AUTHOR_URL } from "@/lib/brand";

/** Quiet, theme-aware attribution line. Rendered in footers across the app
 *  (landing + generated reels + shared pages). */
export function Credit({ className = "" }: { className?: string }) {
  // mailto: links open the mail client in-place; only http(s) links need a new tab.
  const isExternal = /^https?:/i.test(AUTHOR_URL);
  return (
    <p className={`text-[11px] text-[var(--muted)] ${className}`}>
      Designed &amp; developed by{" "}
      <a
        href={AUTHOR_URL}
        {...(isExternal ? { target: "_blank", rel: "noopener noreferrer" } : {})}
        className="font-medium text-[var(--ink)] underline-offset-2 transition hover:text-[var(--accent)] hover:underline"
      >
        {AUTHOR}
      </a>
    </p>
  );
}
