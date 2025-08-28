// Utility to assign stable, high-contrast colors to an unknown number of categories
// Constraints:
// - Start with maximally distinct colors so few categories are clearly different
// - Avoid green and red (reserved for Entrada/Salida overlays)
// - Reserve black for "indeterminados" (unknown/IND)

export const RESERVED_COLORS = {
	red: '#ef4444', // Entrada/Salida red
	green: '#10b981', // Entrada/Salida green
	black: '#000000', // Indeterminados
	white: '#ffffff'
};

// Pre-seeded distinct colors (from Tailwind-like palette), ordered by perceptual contrast.
// Excludes greens and reds; hues chosen to be spread around the circle.
const ANCHOR_COLORS = [
	'#3b82f6', // blue-500 (217°)
	'#f59e0b', // amber-500 (38°)
	'#a855f7', // purple-500 (275°)
	'#06b6d4', // cyan-500 (189°)
	'#facc15', // yellow-400 (50°)
	'#ec4899', // pink-500 (330°)
	'#6366f1', // indigo-500 (239°)
	'#38bdf8', // sky-400 (199°)
	'#c084fc', // violet-400 (280°)
	'#f472b6', // pink-400 (332°)
	'#1d4ed8', // blue-700 (222°)
	'#fb923c' // orange-400 (24°)
];

// Convert HSL to hex for inline styles
function hslToHex(h: number, s: number, l: number): string {
	s /= 100;
	l /= 100;
	const k = (n: number) => (n + h / 30) % 12;
	const a = s * Math.min(l, 1 - l);
	const f = (n: number) => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
	const toHex = (x: number) =>
		Math.round(255 * x)
			.toString(16)
			.padStart(2, '0');
	return `#${toHex(f(0))}${toHex(f(8))}${toHex(f(4))}`;
}

// Generate additional colors using golden-angle hue stepping, skipping forbidden bands
function generateAdditionalColors(count: number, existing: string[] = []): string[] {
	const colors: string[] = [];
	const golden = 137.508; // degrees
	// Start from a blue-ish base that isn't red/green
	let hue = 210;
	const forbidden: Array<[number, number]> = [
		// avoid red band
		[-12, 12].map((x) => (x + 360) % 360) as any
	] as any;
	// push also a broader green band around 120°
	forbidden.push([100, 140]);

	const tooClose = (h: number, hs: number[]): boolean => {
		const minDelta = 14; // degrees minimal separation
		return hs.some((eh) => {
			let d = Math.abs(((h - eh + 540) % 360) - 180);
			return d < minDelta;
		});
	};

	const existingHues = existing.map(hexToHue).filter((h) => h !== null) as number[];

	let i = 0;
	while (colors.length < count && i < count * 20) {
		hue = (hue + golden) % 360;
		const inForbidden = forbidden.some(([a, b]) => {
			if (a <= b) return hue >= a && hue <= b;
			// wrapped interval
			return hue >= a || hue <= b;
		});
		if (inForbidden) {
			i++;
			continue;
		}
		const sat = 80; // vivid
		const light = 52; // balanced on dark backgrounds
		const hex = hslToHex(hue, sat, light);
		const newHue = hue;
		if (
			!tooClose(newHue, existingHues) &&
			!tooClose(
				newHue,
				colors.map(hexToHue).filter((x): x is number => x !== null)
			)
		) {
			colors.push(hex);
		}
		i++;
	}
	return colors;
}

function hexToHue(hex: string): number | null {
	const m = /^#?([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i.exec(hex);
	if (!m) return null;
	const r = parseInt(m[1], 16) / 255;
	const g = parseInt(m[2], 16) / 255;
	const b = parseInt(m[3], 16) / 255;
	const max = Math.max(r, g, b),
		min = Math.min(r, g, b);
	const d = max - min;
	if (d === 0) return 0;
	let h = 0;
	switch (max) {
		case r:
			h = ((g - b) / d) % 6;
			break;
		case g:
			h = (b - r) / d + 2;
			break;
		case b:
			h = (r - g) / d + 4;
			break;
	}
	h = Math.round(h * 60);
	if (h < 0) h += 360;
	return h;
}

export function getCategoryPalette(n: number): string[] {
	if (n <= ANCHOR_COLORS.length) return ANCHOR_COLORS.slice(0, n);
	const extra = generateAdditionalColors(n - ANCHOR_COLORS.length, ANCHOR_COLORS);
	return [...ANCHOR_COLORS, ...extra].slice(0, n);
}

export function getCategoryColorMap(categories: string[]): Map<string, string> {
	const cats = categories.filter(Boolean);
	const palette = getCategoryPalette(cats.length);
	const map = new Map<string, string>();
	cats.forEach((c, i) => {
		// Reserve black for explicit IND/unknown categories only
		if (
			c.toUpperCase() === 'IND' ||
			c.toUpperCase() === 'UNKNOWN' ||
			c.toUpperCase() === 'INDETERMINADO'
		) {
			map.set(c, RESERVED_COLORS.black);
		} else {
			map.set(c, palette[i]);
		}
	});
	return map;
}

export function getCategoryColor(category: string, categories: string[]): string {
	if (!category) return RESERVED_COLORS.black;
	if (
		category.toUpperCase() === 'IND' ||
		category.toUpperCase() === 'UNKNOWN' ||
		category.toUpperCase() === 'INDETERMINADO'
	) {
		return RESERVED_COLORS.black;
	}
	const map = getCategoryColorMap(categories);
	return map.get(category) ?? RESERVED_COLORS.black;
}
