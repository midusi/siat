import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	// Consult https://svelte.dev/docs/kit/integrations
	// for more information about preprocessors
	preprocess: vitePreprocess(),

	kit: {
		// adapter-node builds the app for Node.js production deployment
		adapter: adapter({
			out: 'build',
			// Increase body size limit to 100MB for video uploads
			envPrefix: ''
		}),
		csrf: {
			checkOrigin: false
		}
	}
};

export default config;
