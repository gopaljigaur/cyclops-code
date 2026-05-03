import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightLlmsTxt from 'starlight-llms-txt';

export default defineConfig({
  site: 'https://code.gopalji.me',
  integrations: [
    starlight({
      plugins: [starlightLlmsTxt()],
      title: 'Cyclops Code',
      description: 'A coding agent for your terminal. Any model.',
      favicon: '/favicon.svg',
      defaultLocale: 'en',
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/gopaljigaur/cyclops-code' },
      ],
      sidebar: [
        {
          label: 'Start Here',
          items: [
            { label: 'Introduction', slug: 'index' },
            { label: 'Getting Started', slug: 'getting-started' },
          ],
        },
        {
          label: 'Guides',
          items: [
            { label: 'The REPL', slug: 'guides/repl' },
            { label: 'Tool Approval', slug: 'guides/tool-approval' },
            { label: 'Built-in Tools', slug: 'guides/tools' },
            { label: 'MCP Servers', slug: 'guides/mcp' },
            { label: 'Models', slug: 'guides/models' },
            { label: 'Configuration', slug: 'guides/configuration' },
            { label: 'Sessions', slug: 'guides/sessions' },
          ],
        },
      ],
      customCss: ['./src/styles/custom.css'],
      editLink: {
        baseUrl: 'https://github.com/gopaljigaur/cyclops-code/edit/main/website/',
      },
    }),
  ],
});
