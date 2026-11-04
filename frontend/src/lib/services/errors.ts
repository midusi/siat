type ErrorBody = {
	detail?: string;
	field?: string;
};

const UNAVAILABLE_STATUSES: Array<number> = [502, 503, 504];
const CONNECTION_ERROR_MESSAGE: string = 'No se pudo conectar con el servidor';

export class ApiError extends Error {
	constructor(
		message: string,
		public field?: string
	) {
		super(message);
		this.name = 'ApiError';
	}
}

export const errorMessage = (
	error: unknown,
	fallback: string = CONNECTION_ERROR_MESSAGE
): string => (error instanceof ApiError ? error.message : fallback);

export const apiError = async (res: Response, fallback: string): Promise<ApiError> => {
	if (UNAVAILABLE_STATUSES.includes(res.status)) {
		return new ApiError(CONNECTION_ERROR_MESSAGE);
	}
	const body: ErrorBody | null = await res.json().catch((): ErrorBody => ({}));
	return new ApiError(body?.detail ?? fallback, body?.field);
};
