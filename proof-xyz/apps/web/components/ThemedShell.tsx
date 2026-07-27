import { getTheme } from "@/lib/themes";

/** Page shell that supplies the theme CSS variables.
 *
 * Every themed component reads var(--ink) / var(--surface) / var(--accent),
 * and those are set inline on the root element — globals.css deliberately
 * defines no :root fallbacks. Any route that isn't the interactive Landing or
 * ProfileView must therefore wrap its content in this, or it renders unstyled.
 */
export function ThemedShell({
  children,
  themeId = "midnight",
}: {
  children: React.ReactNode;
  themeId?: string;
}) {
  const theme = getTheme(themeId);
  return (
    <main
      className="proof-root flex min-h-[100dvh] flex-col items-center px-6 py-16"
      style={theme.vars as React.CSSProperties}
    >
      {children}
    </main>
  );
}
