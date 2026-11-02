import type { Variant } from '$lib/types/variant';

export const VARIANT_CLASSES: Record<Variant, string> = {
	default: 'border-white/20 bg-white/10 text-white/90',
	danger: 'border-red-600/50 bg-red-600/15 text-red-100',
	success: 'border-green-500/40 bg-green-400/12 text-green-100',
	warning: 'border-amber-400/40 bg-amber-300/12 text-amber-100',
	info: 'border-sky-400/40 bg-sky-300/12 text-sky-100'
};

export const VARIANT_HOVER_CLASSES: Record<Variant, string> = {
	default: 'hover:bg-white/20',
	danger: 'hover:bg-red-600/25',
	success: 'hover:bg-green-400/20',
	warning: 'hover:bg-amber-300/20',
	info: 'hover:bg-sky-300/20'
};
