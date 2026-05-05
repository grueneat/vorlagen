import { defineConfig } from 'astro/config';

// Currently deployed at https://grueneat.github.io/vorlagen/ (project page).
//
// TODO: switch to custom domain vorlagen.gruene.at once the DNS CNAME
// (vorlagen.gruene.at → grueneat.github.io) is in place. Steps:
//   1. Set `base: '/'` and `site: 'https://vorlagen.gruene.at'` here.
//   2. Add a file `site/public/CNAME` containing `vorlagen.gruene.at`.
//   3. Configure GitHub Pages custom domain:
//        gh api -X PUT repos/GrueneAT/vorlagen/pages -f cname=vorlagen.gruene.at
//   4. Push. The github.io URL will redirect to the custom domain.
export default defineConfig({
  site: 'https://grueneat.github.io',
  base: '/vorlagen/',
  trailingSlash: 'always',
  outDir: './dist',
  build: {
    inlineStylesheets: 'auto',
  },
});
