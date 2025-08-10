export const handleFetch: typeof fetch = async (input, init) => {
    return fetch(input, {
        ...init,
        credentials: 'include'
    });
};
