import { on } from 'svelte/events';

import type { Action, ActionReturn } from 'svelte/action';

type DoubleClickHandler = () => void;
type Timer = ReturnType<typeof setTimeout>;

const CAPTURE: AddEventListenerOptions = { capture: true };
const CONTROLS_BAR_HEIGHT_PX: number = 48;
const DOUBLE_CLICK_DELAY_MS: number = 200;

const isOnControlsBar = (video: HTMLVideoElement, clientY: number): boolean => {
	const rect: DOMRect = video.getBoundingClientRect();
	return clientY - rect.top >= rect.height - CONTROLS_BAR_HEIGHT_PX;
};

const togglePlayback = (video: HTMLVideoElement): void => {
	if (video.paused) {
		video.play();
	} else {
		video.pause();
	}
};

export const videoClicks: Action<HTMLElement, DoubleClickHandler> = (
	node: HTMLElement,
	onDoubleClick: DoubleClickHandler
): ActionReturn<DoubleClickHandler> => {
	let onDouble: DoubleClickHandler = onDoubleClick;
	let timer: Timer | null = null;

	const cancelPending = (): void => {
		if (timer) {
			clearTimeout(timer);
		}
		timer = null;
	};

	const swallow = (ev: MouseEvent): void => {
		ev.preventDefault();
		ev.stopImmediatePropagation();
		cancelPending();
	};

	const onClick = (ev: MouseEvent): void => {
		const video: EventTarget | null = ev.target;
		if (!(video instanceof HTMLVideoElement) || isOnControlsBar(video, ev.clientY)) {
			return;
		}
		swallow(ev);
		timer = setTimeout(() => {
			timer = null;
			togglePlayback(video);
		}, DOUBLE_CLICK_DELAY_MS);
	};

	const onDblClick = (ev: MouseEvent): void => {
		swallow(ev);
		onDouble();
	};

	const offClick: () => void = on(node, 'click', onClick, CAPTURE);
	const offDblClick: () => void = on(node, 'dblclick', onDblClick, CAPTURE);

	return {
		update: (next: DoubleClickHandler): void => {
			onDouble = next;
		},
		destroy: (): void => {
			cancelPending();
			offClick();
			offDblClick();
		}
	};
};
