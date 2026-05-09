import { api } from '$lib/api/client';
import type {
	CollectionCreateRequest,
	CollectionResponse,
	CollectionUpdateRequest,
	DocumentResponse
} from '$lib/api/types';

export const collectionsApi = {
	list: () => api.get<CollectionResponse[]>('/tenant/collections'),
	create: (body: CollectionCreateRequest) =>
		api.post<CollectionResponse>('/tenant/collections', body),
	get: (id: string) => api.get<CollectionResponse>(`/tenant/collections/${id}`),
	update: (id: string, body: CollectionUpdateRequest) =>
		api.patch<CollectionResponse>(`/tenant/collections/${id}`, body),
	delete: (id: string) => api.del(`/tenant/collections/${id}`),
	reindex: (id: string) => api.post<CollectionResponse>(`/tenant/collections/${id}/reindex`, {}),

	listDocuments: (collectionId: string) =>
		api.get<DocumentResponse[]>(`/tenant/collections/${collectionId}/documents`),
	getDocument: (collectionId: string, documentId: string) =>
		api.get<DocumentResponse>(`/tenant/collections/${collectionId}/documents/${documentId}`),
	uploadDocument: (collectionId: string, file: File) => {
		const formData = new FormData();
		formData.append('file', file);
		return api.upload<DocumentResponse>(
			`/tenant/collections/${collectionId}/documents`,
			formData
		);
	},
	deleteDocument: (collectionId: string, documentId: string) =>
		api.del(`/tenant/collections/${collectionId}/documents/${documentId}`)
};
