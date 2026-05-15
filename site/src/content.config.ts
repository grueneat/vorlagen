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
    category: z.string().optional(),         // 'falzflyer' | 'plakat' | etc
    category_label: z.string().optional(),   // display: 'Falzflyer'
    variant_label: z.string().optional(),    // 'Z-Falz 6-seitig (Portrait)'
    format: z.string().optional(),
    orientation: z.string().optional(),
    pages: z.number().optional(),
    preview_dpi: z.number().optional(),
    previews_for_sla: z.string().optional(),
    audience: z.array(z.string()).optional(),
    sizes: z.array(z.any()).optional(),
    masters: z.array(z.any()).optional(),
    example_pages: z.array(z.any()).optional(),
    slots: z.record(z.any()).optional(),
    preflight: z.record(z.any()).optional(),
    build: z.record(z.any()).optional(),
    asset_policy: z.record(z.any()).optional(),
    brand_overrides: z.array(z.any()).optional(),
    ci_overrides: z.record(z.any()).optional(),
    idml_source: z.string().optional(),
    _downloads: z.array(z.any()).optional(),
    _previews: z.array(z.any()).optional(),
  }),
});

// Issue #29 — design-experimentation MVP. Auto-populated by
// tools/experiment_render.py from experiments/<id>/manifest.yml.
const experiments = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/experiments' }),
  schema: z.object({
    id: z.string(),
    subject: z.string(),
    target_weak_area: z.string(),
    contributing_llms: z.array(z.string()),
    created: z.string(),
    prompt_version: z.string().optional(),
    notes: z.string().optional(),
    hypotheses: z.array(z.any()),
  }),
});

export const collections = { templates, experiments };
