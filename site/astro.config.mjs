import { defineConfig } from 'astro/config';

// Deployed at the custom domain https://vorlagen.noe.gruene.at via GitHub
// Pages (DNS CNAME vorlagen.noe.gruene.at → grueneat.github.io). The custom
// domain is bound through site/public/CNAME, served at the dist root.
export default defineConfig({
  site: 'https://vorlagen.noe.gruene.at',
  base: '/',
  trailingSlash: 'always',
  outDir: './dist',
  build: {
    inlineStylesheets: 'auto',
  },
});
