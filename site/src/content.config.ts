import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const templates = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/templates' }),
  schema: z.object({
    id: z.string(),
    version: z.string(),
    title: z.string(),
    description: z.string().optional(),
    type: z.string().optional(),
    format: z.string().optional(),
    pages: z.number().optional(),
    audience: z.array(z.string()).optional(),
    sizes: z.array(z.any()).optional(),
    masters: z.array(z.any()).optional(),
    example_pages: z.array(z.any()).optional(),
    slots: z.record(z.any()).optional(),
    preflight: z.record(z.any()).optional(),
    build: z.record(z.any()).optional(),
    _downloads: z.array(z.any()).optional(),
    _previews: z.array(z.any()).optional(),
  }),
});

export const collections = { templates };
