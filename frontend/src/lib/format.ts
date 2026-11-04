export const formatDate = (value: string | Date): string => {
	const date: Date = typeof value === 'string' ? new Date(value) : value;
	return date.toLocaleDateString('es-AR', { year: '2-digit', month: '2-digit', day: '2-digit' });
};

export const formatDuration = (totalSeconds: number): string => {
	const minutes: number = Math.floor(totalSeconds / 60);
	const seconds: number = Math.floor(totalSeconds % 60);
	return `${minutes}m ${seconds}s`;
};

export const localDateString = (date: Date = new Date()): string => {
	const year: number = date.getFullYear();
	const month: string = String(date.getMonth() + 1).padStart(2, '0');
	const day: string = String(date.getDate()).padStart(2, '0');
	return `${year}-${month}-${day}`;
};
