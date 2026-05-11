import { api } from '$lib/api/client';
import type {
	CollectionCreateRequest,
	CollectionResponse,
	CollectionUpdateRequest,
	DocumentResponse
} from '$lib/api/types';

export interface DocumentContentURLResponse {
	url: string;
	content_type: string;
	expires_in: number;
}

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
		api.del(`/tenant/collections/${collectionId}/documents/${documentId}`),
	createDocument: (collectionId: string, filename: string, content: string) =>
		api.post<DocumentResponse>(`/tenant/collections/${collectionId}/documents/create`, {
			filename,
			content
		}),
	updateDocumentContent: (collectionId: string, documentId: string, content: string) =>
		api.put<DocumentResponse>(
			`/tenant/collections/${collectionId}/documents/${documentId}/content`,
			{ content }
		),

	getDocumentContentUrl: (collectionId: string, documentId: string) =>
		api.get<DocumentContentURLResponse>(
			`/tenant/collections/${collectionId}/documents/${documentId}/content`
		),

	fetchDocumentContent: async (
		collectionId: string,
		documentId: string
	): Promise<{ blob: Blob; contentType: string; url: string }> => {
		const meta = await collectionsApi.getDocumentContentUrl(collectionId, documentId);
		const res = await fetch(meta.url);
		if (!res.ok) throw new Error('Failed to fetch document content');
		const blob = await res.blob();
		return {
			blob,
			contentType: res.headers.get('content-type') || meta.content_type,
			url: meta.url
		};
	}
};
