import type { Action } from 'svelte/action';

const CONTROLS_BAR_HEIGHT_PX = 48;
const DOUBLE_CLICK_DELAY_MS = 200;

export const videoClicks: Action<HTMLElement, () => void> = (node, onDoubleClick) => {
	let onDouble = onDoubleClick;
	let timer: ReturnType<typeof setTimeout> | null = null;

	const cancelPending = () => {
		if (timer) {
			clearTimeout(timer);
		}
		timer = null;
	};

	const onClick = (ev: MouseEvent) => {
		const video = node.querySelector('video');
		if (!video || ev.target !== video) {
			return;
		}
		const rect = video.getBoundingClientRect();
		if (ev.clientY - rect.top >= rect.height - CONTROLS_BAR_HEIGHT_PX) {
			return;
		}
		ev.preventDefault();
		ev.stopImmediatePropagation();
		cancelPending();
		timer = setTimeout(() => {
			timer = null;
			if (video.paused) {
				video.play();
			} else {
				video.pause();
			}
		}, DOUBLE_CLICK_DELAY_MS);
	};

	const onDblClick = (ev: MouseEvent) => {
		ev.preventDefault();
		ev.stopImmediatePropagation();
		cancelPending();
		onDouble?.();
	};

	node.addEventListener('click', onClick, { capture: true });
	node.addEventListener('dblclick', onDblClick, { capture: true });

	return {
		update(next) {
			onDouble = next;
		},
		destroy() {
			cancelPending();
			node.removeEventListener('click', onClick, { capture: true });
			node.removeEventListener('dblclick', onDblClick, { capture: true });
		}
	};
};
