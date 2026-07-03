import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		host: true, // binds 0.0.0.0
		
		// old, for testing
		//allowedHosts: ['traffic-analysis-demo.duckdns.org'],

		// If your public URL is HTTPS (via Nginx + TLS), enable this:
		// hmr: { host: 'traffic-analysis-demo.duckdns.org', protocol: 'wss', clientPort: 443 }
		// If it’s plain HTTP on port 80, use:
		// hmr: { host: 'traffic-analysis-demo.duckdns.org', protocol: 'ws', clientPort: 80 }
	},
});
