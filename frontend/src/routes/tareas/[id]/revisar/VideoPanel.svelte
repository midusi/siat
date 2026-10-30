<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { RESERVED_COLORS } from '$lib/colors';
	import * as review from './review';
	import RouteOverlay from './RouteOverlay.svelte';
	import { videoClicks } from '$lib/actions/videoClicks';
	import ZonesOverlay from './ZonesOverlay.svelte';

	type DataFrames = { first: number; last: number };
	type Props = {
		activeTrackId?: string | null;
		excludedZones: Array<Array<review.Vertex>>;
		height?: number;
		indeterminados: review.Indeterminados;
		liveIds?: Set<string>;
		onbboxclick: (trackId: string) => void;
		roadsIn: Array<review.RoadPoly>;
		roadsOut: Array<review.RoadPoly>;
		trackColor: (trackId: string) => string;
		trackHistory: review.TrackHistory;
		videoFps: number;
		videoHeight: number;
		videoPath: string;
		videoWidth: number;
	};
	type Timer = ReturnType<typeof setTimeout>;

	const ROUTE_ANIMATION_MS: number = 320;
	const ROUTE_FADE_MS: number = 500;
	const SEEK_BACK_TOLERANCE_S: number = 0.05;

	let {
		activeTrackId = $bindable(null),
		excludedZones,
		height = $bindable(0),
		indeterminados,
		liveIds = $bindable(new Set()),
		onbboxclick,
		roadsIn,
		roadsOut,
		trackColor,
		trackHistory,
		videoFps,
		videoHeight,
		videoPath,
		videoWidth
	}: Props = $props();

	let generalDisplayBBoxes: Array<review.GeneralBBox> = $state([]);
	let hideOtherBBoxes: boolean = $state(false);
	let isFullscreen: boolean = $state(false);
	let isSelectionActive: boolean = $state(false);
	let lastProcessedFrame: number = -1;
	let lastVideoTime: number = 0;
	let overlayFrameId: number | null = null;
	let pausedAtMs: number = 0;
	let pausedAtVideoTime: number = 0;
	let playbackBoundingBoxes: Array<review.DisplayableBBox> = $state([]);
	let renderedWidth: number = $state(0);
	let routeAnimateKey: number = $state(0);
	let routeAnimating: boolean = $state(false);
	let routeAnimTimer: Timer | null = null;
	let routeFadeTimer: Timer | null = null;
	let routeFadingOut: boolean = $state(false);
	let routeFutureSegments: Array<Array<review.Point>> = $state([]);
	let routePastSegments: Array<Array<review.Point>> = $state([]);
	let selectedBoxRect: review.Rect | null = $state(null);
	let selectedTrackId: string | null = $state(null);
	let showExcluded: boolean = $state(false);
	let sourceHeight: number = $state(0);
	let sourceWidth: number = $state(0);
	let videoContainerEl: HTMLDivElement | null = $state(null);
	let videoDuration: number = $state(0);
	let videoElement: HTMLVideoElement | null = $state(null);
	let wasPlaying: boolean = false;

	const activePlaybackBoxes: Array<review.DisplayableBBox> = $derived(
		playbackBoundingBoxes.filter((b) => indeterminados[b.id])
	);
	const generalBBoxesByFrame: Map<number, Array<review.GeneralBBox>> = $derived(
		review.buildFrameMap(trackHistory)
	);
	const dataFrames: DataFrames | null = $derived.by(() => {
		const frames: Array<number> = Array.from(generalBBoxesByFrame.keys());
		return frames.length ? { first: Math.min(...frames), last: Math.max(...frames) } : null;
	});
	const hasExcludedZones: boolean = $derived(excludedZones.length > 0);
	const excludedLabel: string = $derived.by(() => {
		if (!hasExcludedZones) {
			return 'No hay zonas excluidas';
		}
		return showExcluded ? 'Ocultar zonas excluidas' : 'Mostrar zonas excluidas';
	});
	const indeterminadosByFrame: Map<number, Array<review.AppearingBox>> = $derived(
		review.groupByFirstAppearance(indeterminados)
	);
	const videoScale: review.Scale = $derived.by(() => {
		const vw: number = sourceWidth || videoWidth;
		const vh: number = sourceHeight || videoHeight;
		if (!vw || !vh || !renderedWidth || !height) {
			return { x: 1, y: 1 };
		}
		return { x: renderedWidth / vw, y: height / vh };
	});
	const visibleGeneralBBoxes: Array<review.GeneralBBox> = $derived.by(() => {
		if (hideOtherBBoxes && selectedTrackId) {
			return generalDisplayBBoxes.filter((b) => b.id === selectedTrackId);
		}
		return generalDisplayBBoxes;
	});
	const visiblePlaybackBoxes: Array<review.DisplayableBBox> = $derived.by(() => {
		if (!hideOtherBBoxes) {
			return activePlaybackBoxes;
		}
		if (!selectedTrackId) {
			return [];
		}
		return activePlaybackBoxes.filter((b) => b.id === selectedTrackId);
	});

	$effect(() => {
		liveIds = new Set(activePlaybackBoxes.map((b) => b.id));
	});

	$effect(() => {
		if (videoScale && generalBBoxesByFrame) {
			untrack(() => {
				if (videoElement?.paused) {
					updateOverlaysForCurrentFrame();
				}
			});
		}
	});

	onMount(() => stopOverlayLoop);

	export const focusTrack = (trackId: string, frame: number): void => {
		if (!videoElement) {
			return;
		}
		videoElement.pause();
		videoElement.currentTime = computeTimeFromFrame(frame);
		selectTrack(trackId);
		hideOtherBBoxes = true;
		updateOverlaysForCurrentFrame();
	};

	export const retargetSelection = (fromId: string, toId: string | null): void => {
		if (selectedTrackId !== fromId) {
			return;
		}
		if (toId) {
			selectedTrackId = toId;
		} else {
			clearSelection();
		}
	};

	const getFrameRange = (): review.FrameRange | null => {
		const dur: number = videoElement?.duration ?? videoDuration ?? 0;
		if (dur <= 0 || !dataFrames) {
			return null;
		}
		return { dur, ...dataFrames };
	};

	const computeCurrentFrameFromTime = (timeSec: number): number =>
		review.timeToFrame(timeSec, getFrameRange(), videoFps);

	const computeTimeFromFrame = (frame: number): number =>
		review.frameToTime(frame, getFrameRange(), videoFps);

	const toScreenRect = (box: review.Box): review.Rect | null => {
		if (!videoElement) {
			return null;
		}
		return review.toScaledClampedRect(box, videoScale, {
			width: videoElement.clientWidth,
			height: videoElement.clientHeight
		});
	};

	const getFadeClock = (): number => {
		if (!videoElement) {
			return 0;
		}
		if (!videoElement.paused) {
			return videoElement.currentTime;
		}
		return pausedAtVideoTime + (performance.now() - pausedAtMs) / 1000;
	};

	const anchorPausedClock = (): void => {
		if (videoElement) {
			pausedAtVideoTime = videoElement.currentTime;
			pausedAtMs = performance.now();
		}
	};

	const resetPlayback = (): void => {
		hideOtherBBoxes = false;
		activeTrackId = null;
		playbackBoundingBoxes = [];
		if (videoElement) {
			lastVideoTime = videoElement.currentTime;
			lastProcessedFrame = computeCurrentFrameFromTime(videoElement.currentTime) - 1;
		}
	};

	const addAppearingBoxes = (currentFrame: number): void => {
		if (currentFrame <= lastProcessedFrame) {
			return;
		}
		const added: Array<review.DisplayableBBox> = [];
		for (let frame = lastProcessedFrame + 1; frame <= currentFrame; frame++) {
			for (const info of indeterminadosByFrame.get(frame) ?? []) {
				added.push({
					id: info.trackId,
					bbox: info.bbox,
					hideAtTime: computeTimeFromFrame(frame) + review.FADE_OUT_DURATION_SECONDS,
					opacity: 1
				});
			}
		}
		if (added.length > 0) {
			playbackBoundingBoxes = [...playbackBoundingBoxes, ...added];
		}
	};

	const overlayTick = (): void => {
		if (!videoElement) {
			overlayFrameId = null;
			return;
		}
		const playing: boolean = !videoElement.paused;
		if (playing && !wasPlaying) {
			resetPlayback();
		}
		if (!playing && wasPlaying) {
			anchorPausedClock();
		}
		wasPlaying = playing;

		let currentFrame: number = lastProcessedFrame;
		if (playing) {
			const currentTime: number = videoElement.currentTime;
			currentFrame = computeCurrentFrameFromTime(currentTime);
			if (currentTime + SEEK_BACK_TOLERANCE_S < lastVideoTime) {
				lastProcessedFrame = currentFrame - 1;
				playbackBoundingBoxes = [];
			}
			lastVideoTime = currentTime;
			updateOverlaysForFrame(currentFrame);
		}

		if (playbackBoundingBoxes.length > 0) {
			playbackBoundingBoxes = review.fadeBoxes(
				playbackBoundingBoxes,
				getFadeClock(),
				performance.now()
			);
		}

		if (playing) {
			addAppearingBoxes(currentFrame);
			lastProcessedFrame = currentFrame;
		}

		overlayFrameId =
			playing || playbackBoundingBoxes.length > 0 ? requestAnimationFrame(overlayTick) : null;
	};

	const startOverlayLoop = (): void => {
		if (overlayFrameId === null) {
			overlayFrameId = requestAnimationFrame(overlayTick);
		}
	};

	const stopOverlayLoop = (): void => {
		if (overlayFrameId !== null) {
			cancelAnimationFrame(overlayFrameId);
			overlayFrameId = null;
		}
	};

	const onVideoPause = (): void => {
		anchorPausedClock();
		startOverlayLoop();
	};

	const onVideoSeek = (seeking: boolean): void => {
		if (!videoElement) {
			return;
		}
		if (seeking) {
			lastProcessedFrame = computeCurrentFrameFromTime(videoElement.currentTime) - 1;
		}
		if (videoElement.paused) {
			updateOverlaysForCurrentFrame();
			anchorPausedClock();
			startOverlayLoop();
		}
	};

	const updateOverlaysForFrame = (frame: number): void => {
		generalDisplayBBoxes = generalBBoxesByFrame.get(frame) ?? [];
		if (!selectedTrackId) {
			selectedBoxRect = null;
			return;
		}
		const sel: review.GeneralBBox | undefined = generalDisplayBBoxes.find(
			(b) => b.id === selectedTrackId
		);
		if (sel) {
			selectedBoxRect = toScreenRect(sel.box);
		}
		updateSelectedTrackRoute(frame);
		if (!review.isFrameWithinTrack(trackHistory.get(selectedTrackId) ?? [], frame)) {
			beginClearSelectionWithFade();
		}
	};

	const updateOverlaysForCurrentFrame = (): void => {
		if (!videoElement) {
			return;
		}
		updateOverlaysForFrame(computeCurrentFrameFromTime(videoElement.currentTime));
	};

	const isBlack = (color: string): boolean => color.toLowerCase() === RESERVED_COLORS.black;

	const generalBorderColor = (trackId: string, selected: boolean): string => {
		if (selected) {
			return RESERVED_COLORS.white;
		}
		if (indeterminados[trackId]) {
			return RESERVED_COLORS.black;
		}
		const color: string = trackColor(trackId);
		return isBlack(color) ? RESERVED_COLORS.white : color;
	};

	const hasDarkOutline = (trackId: string, selected: boolean): boolean =>
		!selected && !indeterminados[trackId] && isBlack(trackColor(trackId));

	const selectTrack = (trackId: string): void => {
		selectedTrackId = trackId;
		isSelectionActive = true;
		if (routeFadeTimer) {
			clearTimeout(routeFadeTimer);
		}
		routeFadingOut = false;
		if (routeAnimTimer) {
			clearTimeout(routeAnimTimer);
		}
		routeAnimating = true;
		routeAnimTimer = setTimeout(() => (routeAnimating = false), ROUTE_ANIMATION_MS);
		routeAnimateKey++;
	};

	const clearSelection = (): void => {
		if (routeAnimTimer) {
			clearTimeout(routeAnimTimer);
		}
		if (routeFadeTimer) {
			clearTimeout(routeFadeTimer);
		}
		selectedTrackId = null;
		selectedBoxRect = null;
		routePastSegments = [];
		routeFutureSegments = [];
		routeAnimating = false;
		routeFadingOut = false;
		isSelectionActive = false;
		hideOtherBBoxes = false;
	};

	const beginClearSelectionWithFade = (): void => {
		isSelectionActive = false;
		if (!selectedTrackId && routePastSegments.length === 0 && routeFutureSegments.length === 0) {
			routeFadingOut = false;
			return;
		}
		if (routeFadeTimer) {
			clearTimeout(routeFadeTimer);
		}
		routeFadingOut = true;
		routeFadeTimer = setTimeout(clearSelection, ROUTE_FADE_MS);
	};

	const updateSelectedTrackRoute = (currentFrame: number): void => {
		if (!selectedTrackId) {
			return;
		}
		const trackPoints: Array<review.TrackPoint> = trackHistory.get(selectedTrackId) ?? [];
		if (!videoElement || trackPoints.length === 0) {
			routePastSegments = [];
			routeFutureSegments = [];
			return;
		}
		const toXY = (p: review.TrackPoint): review.Point => review.boxCenterScaled(p.box, videoScale);
		const pastPts: Array<review.Point> = trackPoints
			.filter((p) => p.frame <= currentFrame)
			.map(toXY);
		const futurePts: Array<review.Point> = trackPoints
			.filter((p) => p.frame > currentFrame)
			.map(toXY);
		routePastSegments = review.clipPolyline(pastPts, selectedBoxRect);
		routeFutureSegments = review.clipPolyline(futurePts, selectedBoxRect);
	};

	const showRouteFor = (box: review.GeneralBBox): void => {
		if (selectedTrackId === box.id) {
			if (isSelectionActive) {
				beginClearSelectionWithFade();
			}
			return;
		}
		selectTrack(box.id);
		const currentFrame: number = videoElement
			? computeCurrentFrameFromTime(videoElement.currentTime)
			: 0;
		selectedBoxRect = toScreenRect(box.box);
		updateSelectedTrackRoute(currentFrame);
		onbboxclick(box.id);
	};

	const updateFullscreenState = (): void => {
		isFullscreen = !!document.fullscreenElement && document.fullscreenElement === videoContainerEl;
	};

	const toggleFullscreen = async (): Promise<void> => {
		if (!videoContainerEl) {
			return;
		}
		try {
			if (!document.fullscreenElement) {
				await videoContainerEl.requestFullscreen();
			} else if (document.fullscreenElement === videoContainerEl) {
				await document.exitFullscreen();
			} else {
				await document.exitFullscreen();
				await videoContainerEl.requestFullscreen();
			}
		} catch (e) {
			console.warn('No se pudo cambiar a pantalla completa:', e);
		}
	};
</script>

<svelte:document onfullscreenchange={updateFullscreenState} />

<div
	bind:this={videoContainerEl}
	class="relative rounded overflow-hidden border border-[hsl(var(--border))] bg-black aspect-video glass-card"
	use:videoClicks={toggleFullscreen}
>
	<video
		class="w-full h-full [&::-webkit-media-controls-enclosure]:overflow-hidden [&::-webkit-media-controls-fullscreen-button]:!hidden"
		controls
		controlsList="nodownload nofullscreen"
		disablepictureinpicture
		playsinline
		bind:this={videoElement}
		bind:clientWidth={renderedWidth}
		bind:clientHeight={height}
		bind:videoWidth={sourceWidth}
		bind:videoHeight={sourceHeight}
		bind:duration={videoDuration}
		onloadedmetadata={() => {
			if (selectedTrackId && videoElement) {
				updateSelectedTrackRoute(computeCurrentFrameFromTime(videoElement.currentTime));
			}
		}}
		onplay={startOverlayLoop}
		onpause={onVideoPause}
		onseeking={() => onVideoSeek(true)}
		onseeked={() => onVideoSeek(false)}
		ontimeupdate={() => {
			if (videoElement?.paused) {
				updateOverlaysForCurrentFrame();
			}
		}}
	>
		<source src={videoPath} type="video/mp4" />
		<track kind="captions" />
		Tu navegador no soporta la reproducción de video.
	</video>

	<button
		type="button"
		onclick={toggleFullscreen}
		title={isFullscreen ? 'Salir de pantalla completa' : 'Pantalla completa'}
		class="absolute z-[15] bottom-2 right-2 bg-black/50 hover:bg-black/70 text-white px-3 py-1.5 rounded-md text-sm"
	>
		{isFullscreen ? 'Salir' : 'Full'}
	</button>

	<ZonesOverlay
		{roadsIn}
		{roadsOut}
		excludedZones={showExcluded ? excludedZones : []}
		scale={videoScale}
	/>

	{#each visibleGeneralBBoxes as box (box.id)}
		{@const rect = toScreenRect(box.box)}
		{@const selected = selectedTrackId === box.id}
		{#if rect}
			<button
				type="button"
				aria-label={`Mostrar ruta del vehículo ${box.id}`}
				class={[
					'absolute z-[12] border-2 cursor-pointer transition-[opacity,box-shadow] duration-500',
					selected && 'shadow-glow',
					hasDarkOutline(box.id, selected) && 'shadow-[inset_0_0_0_2px_#000]',
					isSelectionActive && selectedTrackId && !selected && 'opacity-50'
				]}
				style={review.rectStyle(rect)}
				style:border-color={generalBorderColor(box.id, selected)}
				onclick={() => showRouteFor(box)}
			></button>
		{/if}
	{/each}

	{#if selectedTrackId}
		{#key routeAnimateKey}
			<RouteOverlay
				pastSegments={routePastSegments}
				futureSegments={routeFutureSegments}
				animating={routeAnimating}
				fadingOut={routeFadingOut}
			/>
		{/key}
	{/if}

	{#each visiblePlaybackBoxes as box (box.id)}
		{@const rect = toScreenRect(review.parseBoundingBox(box.bbox))}
		{#if rect}
			<div
				class="absolute z-10 border-2 border-black pointer-events-none transition-opacity duration-500"
				style={review.rectStyle(rect)}
				style:opacity={box.opacity}
			>
				<div
					class="absolute bottom-full -left-0.5 mb-[5px] px-2 py-0.5 rounded bg-black/75 text-white font-sans text-xs font-semibold whitespace-nowrap [text-shadow:0_0_5px_rgba(0,0,0,0.9)]"
				>
					<span class="color-dot" style:background={trackColor(box.id)}></span>ID: {box.id}
				</div>
			</div>
		{/if}
	{/each}
</div>

<div class="mt-3">
	<button
		type="button"
		onclick={() => (showExcluded = !showExcluded)}
		class={[
			'rounded-md px-3 py-2 font-semibold transition-colors disabled:opacity-60 disabled:cursor-not-allowed bg-black text-white border border-white',
			showExcluded && 'animate-glow-pulse'
		]}
		disabled={!hasExcludedZones}
		title={excludedLabel}
	>
		{excludedLabel}
	</button>
</div>
