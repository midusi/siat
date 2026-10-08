import { BACKEND_URL } from '$lib/constants';

export interface UploadProgress {
	loaded: number;
	total: number;
	percentage: number;
}

export interface PresignedUploadResponse {
	upload_url: string;
	object_key: string;
	expires_in: number;
}

/** Por encima de este tamaño la subida va por partes. Tiene que coincidir con PART_SIZE_BYTES del backend. */
const MULTIPART_THRESHOLD = 5 * 1024 * 1024;
const MAX_ATTEMPTS = 3;

/**
 * Sube un archivo de video directamente a MinIO usando presigned URLs.
 * Los archivos grandes van en partes de 5 MB: un PUT único de un video de ~1 min
 * corta la conexión en el proxy y el navegador lo reporta como network error.
 */
export async function uploadVideoToMinio(
	file: File,
	onProgress?: (progress: UploadProgress) => void
): Promise<string> {
	if (file.size > MULTIPART_THRESHOLD) {
		return uploadMultipart(file, onProgress);
	}
	return uploadSingle(file, onProgress);
}

async function uploadSingle(
	file: File,
	onProgress?: (progress: UploadProgress) => void
): Promise<string> {
	const data = await postJson<PresignedUploadResponse>('/task/upload/presigned-url', {
		filename: file.name,
		content_type: file.type
	});

	await putWithRetry(data.upload_url, file, file.type, (loaded) => {
		report(onProgress, loaded, file.size);
	});
	report(onProgress, file.size, file.size);
	return data.object_key;
}

interface MultipartInitResponse {
	object_key: string;
	upload_id: string;
	part_size: number;
	part_count: number;
	expires_in: number;
}

async function uploadMultipart(
	file: File,
	onProgress?: (progress: UploadProgress) => void
): Promise<string> {
	const init = await postJson<MultipartInitResponse>('/task/upload/multipart/init', {
		filename: file.name,
		content_type: file.type || 'video/mp4',
		file_size: file.size
	});

	const loaded = new Array<number>(init.part_count).fill(0);
	const reportParts = () => {
		const sum = loaded.reduce((total, part) => total + part, 0);
		report(onProgress, sum, file.size);
	};

	try {
		for (let partNumber = 1; partNumber <= init.part_count; partNumber++) {
			const start = (partNumber - 1) * init.part_size;
			const end = Math.min(start + init.part_size, file.size);
			const chunk = file.slice(start, end);
			const signed = await postJson<{ upload_url: string }>('/task/upload/multipart/part-url', {
				object_key: init.object_key,
				upload_id: init.upload_id,
				part_number: partNumber
			});
			await putWithRetry(signed.upload_url, chunk, undefined, (partLoaded) => {
				loaded[partNumber - 1] = partLoaded;
				reportParts();
			});
			loaded[partNumber - 1] = chunk.size;
			reportParts();
		}

		await postJson('/task/upload/multipart/complete', {
			object_key: init.object_key,
			upload_id: init.upload_id,
			part_count: init.part_count
		});
		return init.object_key;
	} catch (error) {
		await postJson('/task/upload/multipart/abort', {
			object_key: init.object_key,
			upload_id: init.upload_id
		}).catch(() => undefined);
		throw error;
	}
}

function report(
	onProgress: ((progress: UploadProgress) => void) | undefined,
	loaded: number,
	total: number
) {
	if (!onProgress || total <= 0) return;
	onProgress({
		loaded,
		total,
		percentage: Math.min(100, Math.round((loaded / total) * 100))
	});
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
	const response = await fetch(`${BACKEND_URL}${path}`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		credentials: 'include',
		body: JSON.stringify(body)
	});
	if (!response.ok) {
		const error = await response.text();
		throw new Error(error || `Request failed (${response.status})`);
	}
	return response.json() as Promise<T>;
}

function putWithRetry(
	url: string,
	body: Blob,
	contentType: string | undefined,
	onLoaded: (loaded: number) => void
): Promise<void> {
	return (async () => {
		let lastError: Error | null = null;
		for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
			try {
				await putOnce(url, body, contentType, onLoaded);
				return;
			} catch (error) {
				lastError = error instanceof Error ? error : new Error(String(error));
				if (attempt < MAX_ATTEMPTS) {
					await delay(400 * attempt);
				}
			}
		}
		throw lastError ?? new Error('Upload failed due to network error');
	})();
}

function putOnce(
	url: string,
	body: Blob,
	contentType: string | undefined,
	onLoaded: (loaded: number) => void
): Promise<void> {
	return new Promise((resolve, reject) => {
		const xhr = new XMLHttpRequest();
		xhr.open('PUT', url);
		if (contentType) {
			xhr.setRequestHeader('Content-Type', contentType);
		}
		xhr.upload.addEventListener('progress', (event: ProgressEvent) => {
			if (event.lengthComputable) onLoaded(event.loaded);
		});
		xhr.addEventListener('load', () => {
			if (xhr.status >= 200 && xhr.status < 300) {
				resolve();
			} else {
				reject(new Error(`Upload failed with status ${xhr.status}: ${xhr.responseText}`));
			}
		});
		xhr.addEventListener('error', () => {
			reject(new Error('Upload failed due to network error'));
		});
		xhr.addEventListener('abort', () => {
			reject(new Error('Upload was aborted'));
		});
		xhr.send(body);
	});
}

function delay(ms: number): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve, ms));
}
