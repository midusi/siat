export class ApiError extends Error {
    constructor(message: string, public field?: string) {
        super(message);
        this.name = 'ApiError';
    }
}

export const apiError = async (res: Response, fallback: string): Promise<ApiError> => {
    const err = await res.json().catch(() => ({}));
    return new ApiError(err?.detail ?? fallback, err?.field);
}