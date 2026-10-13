export class ApiError extends Error {
    constructor(message: string, public field?: string) {
        super(message);
        this.name = 'ApiError';
    }
}

const UNAVAILABLE_STATUSES = [502, 503, 504];

export const apiError = async (res: Response, fallback: string): Promise<ApiError> => {
    if (UNAVAILABLE_STATUSES.includes(res.status)) {
        return new ApiError('No se pudo conectar con el servidor');
    }
    const err = await res.json().catch(() => ({}));
    return new ApiError(err?.detail ?? fallback, err?.field);
}