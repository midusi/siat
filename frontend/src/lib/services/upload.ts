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

/**
 * Sube un archivo de video directamente a MinIO usando presigned URLs.
 * Esto permite subir archivos de cualquier tamaño sin pasar por el servidor backend.
 * 
 * @param file - El archivo de video a subir
 * @param onProgress - Callback opcional para reportar progreso de subida
 * @returns El object_key del archivo subido en MinIO
 */
export async function uploadVideoToMinio(
	file: File,
	onProgress?: (progress: UploadProgress) => void
): Promise<string> {
	// 1. Obtener URL presignada del backend
	const response = await fetch(`${BACKEND_URL}/task/upload/presigned-url`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		credentials: 'include',
		body: JSON.stringify({
			filename: file.name,
			content_type: file.type
		})
	});

	if (!response.ok) {
		const error = await response.text();
		throw new Error(`Failed to get upload URL: ${error}`);
	}

	const data: PresignedUploadResponse = await response.json();
	const { upload_url, object_key } = data;

	// 2. Upload directo a MinIO con seguimiento de progreso
	return new Promise<string>((resolve, reject) => {
		const xhr = new XMLHttpRequest();

		// Configurar seguimiento de progreso
		xhr.upload.addEventListener('progress', (e: ProgressEvent) => {
			if (e.lengthComputable && onProgress) {
				onProgress({
					loaded: e.loaded,
					total: e.total,
					percentage: Math.round((e.loaded / e.total) * 100)
				});
			}
		});

		// Manejar completado exitoso
		xhr.addEventListener('load', () => {
			if (xhr.status === 200) {
				resolve(object_key);
			} else {
				reject(new Error(`Upload failed with status ${xhr.status}: ${xhr.responseText}`));
			}
		});

		// Manejar errores de red
		xhr.addEventListener('error', () => {
			reject(new Error('Upload failed due to network error'));
		});

		// Manejar cancelación
		xhr.addEventListener('abort', () => {
			reject(new Error('Upload was aborted'));
		});

		// Iniciar upload
		xhr.open('PUT', upload_url);
		xhr.setRequestHeader('Content-Type', file.type);
		xhr.send(file);
	});
}
