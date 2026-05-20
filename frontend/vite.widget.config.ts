import { svelte } from '@sveltejs/vite-plugin-svelte';
import { resolve } from 'node:path';
import { defineConfig } from 'vite';

export default defineConfig({
	envPrefix: 'PUBLIC_',
	plugins: [svelte({ compilerOptions: { css: 'injected' } })],
	resolve: {
		alias: {
			$lib: resolve('./src/lib')
		}
	},
	build: {
		emptyOutDir: false,
		lib: {
			entry: resolve('./src/lib/widget/embed.ts'),
			name: 'GenAIWidget',
			formats: ['iife'],
			fileName: () => 'widget.js'
		},
		outDir: 'static',
		rollupOptions: {
			output: {
				inlineDynamicImports: true
			}
		}
	}
});
