import { ApiError, apiError } from './errors';
import { apiFetch } from '$lib/api';

export type UploadProgress = {
	loaded: number;
	total: number;
	percentage: number;
};

type ProgressCallback = (progress: UploadProgress) => void;

type PresignedUploadResponse = {
	upload_url: string;
	object_key: string;
	expires_in: number;
};

type MultipartInitResponse = {
	object_key: string;
	upload_id: string;
	part_size: number;
	part_count: number;
	expires_in: number;
};

type PartUrlResponse = { upload_url: string };

const UPLOAD_API: string = '/task/upload';
/** Por encima de este tamaño la subida va por partes. Tiene que coincidir con PART_SIZE_BYTES del backend. */
const MULTIPART_THRESHOLD: number = 5 * 1024 * 1024;
const MAX_ATTEMPTS: number = 3;
const RETRY_DELAY_MS: number = 400;
const DEFAULT_CONTENT_TYPE: string = 'video/mp4';
const UPLOAD_ERROR_MESSAGE: string = 'No se pudo subir el video';
const NETWORK_ERROR_MESSAGE: string = 'Error de red al subir el video';

/**
 * Sube un archivo de video directamente a MinIO usando presigned URLs.
 * Los archivos grandes van en partes de 5 MB: un PUT único de un video de ~1 min
 * corta la conexión en el proxy y el navegador lo reporta como network error.
 */
export const uploadVideoToMinio = (file: File, onProgress?: ProgressCallback): Promise<string> =>
	file.size > MULTIPART_THRESHOLD
		? uploadMultipart(file, onProgress)
		: uploadSingle(file, onProgress);

const uploadSingle = async (file: File, onProgress?: ProgressCallback): Promise<string> => {
	const contentType: string = file.type || DEFAULT_CONTENT_TYPE;
	const data: PresignedUploadResponse = await postUpload<PresignedUploadResponse>(
		'/presigned-url',
		{ filename: file.name, content_type: contentType }
	);

	await putWithRetry(data.upload_url, file, contentType, (loaded: number): void => {
		report(onProgress, loaded, file.size);
	});
	report(onProgress, file.size, file.size);
	return data.object_key;
};

const uploadMultipart = async (file: File, onProgress?: ProgressCallback): Promise<string> => {
	const init: MultipartInitResponse = await postUpload<MultipartInitResponse>('/multipart/init', {
		filename: file.name,
		content_type: file.type || DEFAULT_CONTENT_TYPE,
		file_size: file.size
	});

	const loadedByPart: Array<number> = new Array<number>(init.part_count).fill(0);
	const reportParts = (): void => {
		const loaded: number = loadedByPart.reduce(
			(total: number, part: number): number => total + part,
			0
		);
		report(onProgress, loaded, file.size);
	};

	try {
		for (let partNumber: number = 1; partNumber <= init.part_count; partNumber++) {
			const start: number = (partNumber - 1) * init.part_size;
			const end: number = Math.min(start + init.part_size, file.size);
			const chunk: Blob = file.slice(start, end);
			const signed: PartUrlResponse = await postUpload<PartUrlResponse>('/multipart/part-url', {
				object_key: init.object_key,
				upload_id: init.upload_id,
				part_number: partNumber
			});
			await putWithRetry(signed.upload_url, chunk, undefined, (partLoaded: number): void => {
				loadedByPart[partNumber - 1] = partLoaded;
				reportParts();
			});
			loadedByPart[partNumber - 1] = chunk.size;
			reportParts();
		}

		await postUpload('/multipart/complete', {
			object_key: init.object_key,
			upload_id: init.upload_id,
			part_count: init.part_count
		});
		return init.object_key;
	} catch (error) {
		await postUpload('/multipart/abort', {
			object_key: init.object_key,
			upload_id: init.upload_id
		}).catch((): undefined => undefined);
		throw error;
	}
};

const report = (onProgress: ProgressCallback | undefined, loaded: number, total: number): void => {
	if (!onProgress || total <= 0) {
		return;
	}
	onProgress({
		loaded,
		total,
		percentage: Math.min(100, Math.round((loaded / total) * 100))
	});
};

const postUpload = async <T = unknown>(path: string, body: unknown): Promise<T> => {
	const res: Response = await apiFetch(`${UPLOAD_API}${path}`, {
		method: 'POST',
		body: JSON.stringify(body)
	});
	if (!res.ok) {
		throw await apiError(res, UPLOAD_ERROR_MESSAGE);
	}
	return (await res.json()) as T;
};

const putWithRetry = async (
	url: string,
	body: Blob,
	contentType: string | undefined,
	onLoaded: (loaded: number) => void
): Promise<void> => {
	let lastError: Error | null = null;
	for (let attempt: number = 1; attempt <= MAX_ATTEMPTS; attempt++) {
		try {
			await putOnce(url, body, contentType, onLoaded);
			return;
		} catch (error) {
			lastError = error instanceof Error ? error : new Error(String(error));
			if (attempt < MAX_ATTEMPTS) {
				await delay(RETRY_DELAY_MS * attempt);
			}
		}
	}
	throw lastError ?? new ApiError(NETWORK_ERROR_MESSAGE);
};

const putOnce = (
	url: string,
	body: Blob,
	contentType: string | undefined,
	onLoaded: (loaded: number) => void
): Promise<void> =>
	new Promise((resolve: () => void, reject: (error: ApiError) => void): void => {
		const xhr: XMLHttpRequest = new XMLHttpRequest();
		xhr.open('PUT', url);
		if (contentType) {
			xhr.setRequestHeader('Content-Type', contentType);
		}
		xhr.upload.addEventListener('progress', (event: ProgressEvent): void => {
			if (event.lengthComputable) {
				onLoaded(event.loaded);
			}
		});
		xhr.addEventListener('load', (): void => {
			if (xhr.status >= 200 && xhr.status < 300) {
				resolve();
			} else {
				reject(new ApiError(`${UPLOAD_ERROR_MESSAGE} (estado ${xhr.status})`));
			}
		});
		xhr.addEventListener('error', (): void => {
			reject(new ApiError(NETWORK_ERROR_MESSAGE));
		});
		xhr.addEventListener('abort', (): void => {
			reject(new ApiError('La subida del video fue cancelada'));
		});
		xhr.send(body);
	});

const delay = (ms: number): Promise<void> =>
	new Promise((resolve: () => void): void => {
		setTimeout(resolve, ms);
	});
