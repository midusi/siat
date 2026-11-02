import type { IconName } from '$lib/components/Icon.svelte';

export type MenuItem = {
	id: string;
	label: string;
	path: string;
	icon: IconName;
	adminOnly?: boolean;
};
