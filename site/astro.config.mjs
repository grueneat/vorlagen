import { defineConfig } from 'astro/config';

// Deployed at https://vorlagen.gruene.at/ via GitHub Pages custom domain
// (CNAME file in public/ + Pages custom-domain config). Pages redirects
// https://grueneat.github.io/vorlagen/* to the canonical custom domain.
export default defineConfig({
  site: 'https://vorlagen.gruene.at',
  base: '/',
  trailingSlash: 'always',
  outDir: './dist',
  build: {
    inlineStylesheets: 'auto',
  },
});
