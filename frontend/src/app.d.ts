// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	namespace App {
		interface Locals {
			user: {
				id: number;
				username: string;
				email: string;
				first_name?: string | null;
				last_name?: string | null;
				role: string;
				active: boolean;
			} | null;
		}
		interface PageData {
			user: App.Locals['user'];
		}
		// interface PageState {}
		// interface Platform {}
	}
}

export { };
