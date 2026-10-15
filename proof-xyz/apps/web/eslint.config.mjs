import { dirname } from "path";
import { fileURLToPath } from "url";

import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({ baseDirectory: dirname(fileURLToPath(import.meta.url)) });

const eslintConfig = [
  { ignores: [".next/**", "node_modules/**", "next-env.d.ts"] },
  // Next's recommended rules (React, hooks, a11y basics, Core Web Vitals) plus
  // its TypeScript rules; "prettier" last turns off rules that fight formatting.
  ...compat.extends("next/core-web-vitals", "next/typescript", "prettier"),
];

export default eslintConfig;
