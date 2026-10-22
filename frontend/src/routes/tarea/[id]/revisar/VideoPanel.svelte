<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import * as review from './review';
	import RouteOverlay from './RouteOverlay.svelte';
	import { videoClicks } from '$lib/actions/videoClicks';
	import ZonesOverlay from './ZonesOverlay.svelte';

	type Timer = ReturnType<typeof setTimeout>;

	const ROUTE_ANIMATION_MS = 320;
	const ROUTE_FADE_MS = 500;
	const SEEK_BACK_TOLERANCE_S = 0.05;

	let {
		videoPath,
		videoFps,
		videoWidth,
		videoHeight,
		roadsIn,
		roadsOut,
		excludedZones,
		trackHistory,
		indeterminados,
		trackColor,
		activeTrackId = $bindable(null),
		height = $bindable(0),
		liveIds = $bindable(new Set()),
		onbboxclick
	}: {
		videoPath: string;
		videoFps: number;
		videoWidth: number;
		videoHeight: number;
		roadsIn: review.RoadPoly[];
		roadsOut: review.RoadPoly[];
		excludedZones: [number, number][][];
		trackHistory: Map<string, review.TrackPoint[]>;
		indeterminados: review.Indeterminados;
		trackColor: (trackId: string) => string;
		activeTrackId?: string | null;
		height?: number;
		liveIds?: Set<string>;
		onbboxclick: (trackId: string) => void;
	} = $props();

	let generalDisplayBBoxes = $state<review.GeneralBBox[]>([]);
	let hideOtherBBoxes = $state(false);
	let isFullscreen = $state(false);
	let isSelectionActive = $state(false);
	let lastProcessedFrame = -1;
	let lastVideoTime = 0;
	let overlayFrameId: number | null = null;
	let pausedAtMs = 0;
	let pausedAtVideoTime = 0;
	let playbackBoundingBoxes = $state<review.DisplayableBBox[]>([]);
	let renderedWidth = $state(0);
	let routeAnimateKey = $state(0);
	let routeAnimating = $state(false);
	let routeAnimTimer: Timer | null = null;
	let routeFadeTimer: Timer | null = null;
	let routeFadingOut = $state(false);
	let routeFutureSegments = $state<review.Point[][]>([]);
	let routePastSegments = $state<review.Point[][]>([]);
	let selectedBoxRect = $state<review.Rect | null>(null);
	let selectedTrackId = $state<string | null>(null);
	let showExcluded = $state(false);
	let sourceHeight = $state(0);
	let sourceWidth = $state(0);
	let videoContainerEl = $state<HTMLDivElement | null>(null);
	let videoDuration = $state(0);
	let videoElement = $state<HTMLVideoElement | null>(null);
	let wasPlaying = false;

	let generalBBoxesByFrame = $derived(review.buildFrameMap(trackHistory));
	let dataFrames = $derived.by(() => {
		const frames = Array.from(generalBBoxesByFrame.keys());
		return frames.length ? { first: Math.min(...frames), last: Math.max(...frames) } : null;
	});
	let videoScale = $derived.by(() => {
		const vw = sourceWidth || videoWidth;
		const vh = sourceHeight || videoHeight;
		if (!vw || !vh || !renderedWidth || !height) {
			return { x: 1, y: 1 };
		}
		return { x: renderedWidth / vw, y: height / vh };
	});
	let hasExcludedZones = $derived(excludedZones.length > 0);
	let excludedLabel = $derived.by(() => {
		if (!hasExcludedZones) {
			return 'No hay zonas excluidas';
		}
		return showExcluded ? 'Ocultar zonas excluidas' : 'Mostrar zonas excluidas';
	});
	let indeterminadosByFrame = $derived(review.groupByFirstAppearance(indeterminados));
	let activePlaybackBoxes = $derived(playbackBoundingBoxes.filter((b) => indeterminados[b.id]));
	let visibleGeneralBBoxes = $derived.by(() => {
		if (hideOtherBBoxes && selectedTrackId) {
			return generalDisplayBBoxes.filter((b) => b.id === selectedTrackId);
		}
		return generalDisplayBBoxes;
	});
	let visiblePlaybackBoxes = $derived.by(() => {
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

	export const focusTrack = (trackId: string, frame: number) => {
		if (!videoElement) {
			return;
		}
		videoElement.pause();
		videoElement.currentTime = computeTimeFromFrame(frame);
		selectTrack(trackId);
		hideOtherBBoxes = true;
		updateOverlaysForCurrentFrame();
	};

	export const retargetSelection = (fromId: string, toId: string | null) => {
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
		const dur = videoElement?.duration ?? videoDuration ?? 0;
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

	const anchorPausedClock = () => {
		if (videoElement) {
			pausedAtVideoTime = videoElement.currentTime;
			pausedAtMs = performance.now();
		}
	};

	const resetPlayback = () => {
		hideOtherBBoxes = false;
		activeTrackId = null;
		playbackBoundingBoxes = [];
		if (videoElement) {
			lastVideoTime = videoElement.currentTime;
			lastProcessedFrame = computeCurrentFrameFromTime(videoElement.currentTime) - 1;
		}
	};

	const addAppearingBoxes = (currentFrame: number) => {
		if (currentFrame <= lastProcessedFrame) {
			return;
		}
		const added: review.DisplayableBBox[] = [];
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

	const overlayTick = () => {
		if (!videoElement) {
			overlayFrameId = null;
			return;
		}
		const playing = !videoElement.paused;
		if (playing && !wasPlaying) {
			resetPlayback();
		}
		if (!playing && wasPlaying) {
			anchorPausedClock();
		}
		wasPlaying = playing;

		let currentFrame = lastProcessedFrame;
		if (playing) {
			const currentTime = videoElement.currentTime;
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

	const startOverlayLoop = () => {
		if (overlayFrameId === null) {
			overlayFrameId = requestAnimationFrame(overlayTick);
		}
	};

	const stopOverlayLoop = () => {
		if (overlayFrameId !== null) {
			cancelAnimationFrame(overlayFrameId);
			overlayFrameId = null;
		}
	};

	const onVideoPause = () => {
		anchorPausedClock();
		startOverlayLoop();
	};

	const onVideoSeek = (seeking: boolean) => {
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

	const updateOverlaysForFrame = (frame: number) => {
		generalDisplayBBoxes = generalBBoxesByFrame.get(frame) ?? [];
		if (!selectedTrackId) {
			selectedBoxRect = null;
			return;
		}
		const sel = generalDisplayBBoxes.find((b) => b.id === selectedTrackId);
		if (sel) {
			selectedBoxRect = toScreenRect(sel.box);
		}
		updateSelectedTrackRoute(frame);
		if (!review.isFrameWithinTrack(trackHistory.get(selectedTrackId) ?? [], frame)) {
			beginClearSelectionWithFade();
		}
	};

	const updateOverlaysForCurrentFrame = () => {
		if (!videoElement) {
			return;
		}
		updateOverlaysForFrame(computeCurrentFrameFromTime(videoElement.currentTime));
	};

	const isBlack = (color: string): boolean => color.toLowerCase() === '#000000';

	const generalBorderColor = (trackId: string, selected: boolean): string => {
		if (selected) {
			return '#ffffff';
		}
		if (indeterminados[trackId]) {
			return '#000000';
		}
		const color = trackColor(trackId);
		return isBlack(color) ? '#ffffff' : color;
	};

	const hasDarkOutline = (trackId: string, selected: boolean): boolean =>
		!selected && !indeterminados[trackId] && isBlack(trackColor(trackId));

	const selectTrack = (trackId: string) => {
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

	const clearSelection = () => {
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

	const beginClearSelectionWithFade = () => {
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

	const updateSelectedTrackRoute = (currentFrame: number) => {
		if (!selectedTrackId) {
			return;
		}
		const trackPoints = trackHistory.get(selectedTrackId) ?? [];
		if (!videoElement || trackPoints.length === 0) {
			routePastSegments = [];
			routeFutureSegments = [];
			return;
		}
		const toXY = (p: review.TrackPoint) => review.boxCenterScaled(p.box, videoScale);
		const pastPts = trackPoints.filter((p) => p.frame <= currentFrame).map(toXY);
		const futurePts = trackPoints.filter((p) => p.frame > currentFrame).map(toXY);
		routePastSegments = review.clipPolyline(pastPts, selectedBoxRect);
		routeFutureSegments = review.clipPolyline(futurePts, selectedBoxRect);
	};

	const showRouteFor = (box: review.GeneralBBox) => {
		if (selectedTrackId === box.id) {
			if (isSelectionActive) {
				beginClearSelectionWithFade();
			}
			return;
		}
		selectTrack(box.id);
		const currentFrame = videoElement ? computeCurrentFrameFromTime(videoElement.currentTime) : 0;
		selectedBoxRect = toScreenRect(box.box);
		updateSelectedTrackRoute(currentFrame);
		onbboxclick(box.id);
	};

	const updateFullscreenState = () => {
		isFullscreen = !!document.fullscreenElement && document.fullscreenElement === videoContainerEl;
	};

	const toggleFullscreen = async () => {
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
