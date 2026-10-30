type HueBand = [number, number];

type ReservedColor = 'red' | 'green' | 'black' | 'white';

const ANCHOR_COLORS: Array<string> = [
	'#3b82f6',
	'#f59e0b',
	'#a855f7',
	'#06b6d4',
	'#facc15',
	'#ec4899',
	'#6366f1',
	'#38bdf8',
	'#c084fc',
	'#f472b6',
	'#1d4ed8',
	'#fb923c'
];

export const RESERVED_COLORS: Readonly<Record<ReservedColor, string>> = {
	red: '#ef4444',
	green: '#10b981',
	black: '#000000',
	white: '#ffffff'
};

const GOLDEN_ANGLE: number = 137.508;
const START_HUE: number = 210;
const FORBIDDEN_HUE_BANDS: Array<HueBand> = [
	[348, 12],
	[100, 140]
];
const MIN_HUE_DISTANCE: number = 14;
const MAX_ATTEMPTS_PER_COLOR: number = 20;
const GENERATED_SATURATION: number = 80;
const GENERATED_LIGHTNESS: number = 52;

const INDETERMINATE_CATEGORIES: Set<string> = new Set(['IND', 'UNKNOWN', 'INDETERMINADO']);

const hslToHex = (hue: number, saturation: number, lightness: number): string => {
	const saturationRatio: number = saturation / 100;
	const lightnessRatio: number = lightness / 100;
	const amplitude: number = saturationRatio * Math.min(lightnessRatio, 1 - lightnessRatio);
	const channelValue = (channelOffset: number): number => {
		const position: number = (channelOffset + hue / 30) % 12;
		return lightnessRatio - amplitude * Math.max(-1, Math.min(position - 3, 9 - position, 1));
	};
	const toHex = (value: number): string =>
		Math.round(255 * value)
			.toString(16)
			.padStart(2, '0');
	const red: string = toHex(channelValue(0));
	const green: string = toHex(channelValue(8));
	const blue: string = toHex(channelValue(4));
	return `#${red}${green}${blue}`;
};

const hexToHue = (hex: string): number | null => {
	const match: RegExpExecArray | null = /^#?([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i.exec(hex);
	if (!match) {
		return null;
	}
	const red: number = parseInt(match[1], 16) / 255;
	const green: number = parseInt(match[2], 16) / 255;
	const blue: number = parseInt(match[3], 16) / 255;
	const max: number = Math.max(red, green, blue);
	const min: number = Math.min(red, green, blue);
	const chroma: number = max - min;
	if (chroma === 0) {
		return 0;
	}
	let sector: number = 0;
	switch (max) {
		case red:
			sector = ((green - blue) / chroma) % 6;
			break;
		case green:
			sector = (blue - red) / chroma + 2;
			break;
		case blue:
			sector = (red - green) / chroma + 4;
			break;
	}
	const hue: number = Math.round(sector * 60);
	return hue < 0 ? hue + 360 : hue;
};

const isInForbiddenBand = (hue: number): boolean =>
	FORBIDDEN_HUE_BANDS.some(([start, end]: HueBand): boolean =>
		start <= end ? hue >= start && hue <= end : hue >= start || hue <= end
	);

const isTooClose = (hue: number, otherHues: Array<number>): boolean =>
	otherHues.some((otherHue: number): boolean => {
		const distance: number = Math.abs(((hue - otherHue + 540) % 360) - 180);
		return distance < MIN_HUE_DISTANCE;
	});

const toHues = (hexColors: Array<string>): Array<number> =>
	hexColors.map(hexToHue).filter((hue: number | null): hue is number => hue !== null);

const generateAdditionalColors = (count: number): Array<string> => {
	const colors: Array<string> = [];
	const usedHues: Array<number> = toHues(ANCHOR_COLORS);
	let hue: number = START_HUE;
	let attempts: number = 0;

	while (colors.length < count && attempts < count * MAX_ATTEMPTS_PER_COLOR) {
		attempts++;
		hue = (hue + GOLDEN_ANGLE) % 360;
		if (isInForbiddenBand(hue) || isTooClose(hue, usedHues)) {
			continue;
		}
		usedHues.push(hue);
		colors.push(hslToHex(hue, GENERATED_SATURATION, GENERATED_LIGHTNESS));
	}
	return colors;
};

const getCategoryPalette = (count: number): Array<string> => {
	const colors: Array<string> =
		count <= ANCHOR_COLORS.length
			? ANCHOR_COLORS
			: [...ANCHOR_COLORS, ...generateAdditionalColors(count - ANCHOR_COLORS.length)];
	return Array.from(
		{ length: count },
		(_: unknown, index: number): string => colors[index % colors.length]
	);
};

const isIndeterminate = (category: string): boolean =>
	INDETERMINATE_CATEGORIES.has(category.toUpperCase());

export const getCategoryColorMap = (categories: Array<string>): Map<string, string> => {
	const validCategories: Array<string> = categories.filter(Boolean);
	const palette: Array<string> = getCategoryPalette(validCategories.length);
	const colorMap: Map<string, string> = new Map<string, string>();
	validCategories.forEach((category: string, index: number): void => {
		colorMap.set(category, isIndeterminate(category) ? RESERVED_COLORS.black : palette[index]);
	});
	return colorMap;
};

export const getCategoryColor = (category: string, colorMap: Map<string, string>): string => {
	if (!category || isIndeterminate(category)) {
		return RESERVED_COLORS.black;
	}
	return colorMap.get(category) ?? RESERVED_COLORS.black;
};
