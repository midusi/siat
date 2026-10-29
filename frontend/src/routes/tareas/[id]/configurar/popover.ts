import type { Coordinates, Size } from './geometry';

export type PopoverPosition = { top: number; left: number; transform: string };

const DEFAULT_POPOVER_SIZE: Size = { width: 288, height: 230 };
const MARGIN: number = 16;
const OFFSET_Y: number = 15;

/**
 * Ubica el popover debajo del ancla (o arriba si no entra) y lo mantiene
 * dentro del viewport horizontalmente. `anchor` está en coordenadas de viewport.
 */
export const calculatePopoverPosition = (
	anchor: Coordinates,
	popover: Size | null,
	viewport: Size
): PopoverPosition => {
	const { width, height }: Size = popover ?? DEFAULT_POPOVER_SIZE;
	const below: number = anchor.y + OFFSET_Y;
	const top: number =
		below + height > viewport.height - MARGIN ? anchor.y - OFFSET_Y - height : below;
	const halfWidth: number = width / 2;
	const left: number = Math.max(
		halfWidth + MARGIN,
		Math.min(anchor.x, viewport.width - halfWidth - MARGIN)
	);
	return { top, left, transform: 'translate(-50%, 0)' };
};
