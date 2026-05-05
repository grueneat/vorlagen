import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://example.github.io',
  base: '/',
  outDir: './dist',
  build: {
    inlineStylesheets: 'auto',
  },
});
