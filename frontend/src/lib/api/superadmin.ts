import { api } from '$lib/api/client';
import type {
	SuperadminTenantResponse,
	SuperadminTenantCreateRequest,
	SuperadminTenantUpdateRequest,
	SuperadminUserResponse,
	SuperadminUserUpdateRequest,
	SuperadminAgentInstanceResponse,
	SuperadminAuditLogResponse,
	SkillDefinitionResponse,
	SkillDefinitionRequest,
	ToolDefinitionResponse,
	ToolDefinitionRequest,
	EmailTemplateResponse,
	EmailTemplateRequest,
	SystemSettingsResponse,
	SystemSettingsUpdateRequest,
	TenantMemberResponse,
	MessageResponse
} from '$lib/api/types';

const SA = { skipTenant: true } as const;

export const superadminApi = {
	// Tenants
	listTenants: () => api.get<SuperadminTenantResponse[]>('/superadmin/tenants', undefined, SA),
	createTenant: (body: SuperadminTenantCreateRequest) =>
		api.post<SuperadminTenantResponse>('/superadmin/tenants', body, SA),
	getTenant: (id: string) =>
		api.get<SuperadminTenantResponse>(`/superadmin/tenants/${id}`, undefined, SA),
	updateTenant: (id: string, body: SuperadminTenantUpdateRequest) =>
		api.patch<SuperadminTenantResponse>(`/superadmin/tenants/${id}`, body, SA),

	// Users
	listUsers: (params?: Record<string, string>) =>
		api.get<SuperadminUserResponse[]>('/superadmin/users', params, SA),
	getUser: (id: string) =>
		api.get<SuperadminUserResponse>(`/superadmin/users/${id}`, undefined, SA),
	updateUser: (id: string, body: SuperadminUserUpdateRequest) =>
		api.patch<SuperadminUserResponse>(`/superadmin/users/${id}`, body, SA),

	// Registry — skills
	listSkills: () =>
		api.get<SkillDefinitionResponse[]>('/superadmin/registry/skills', undefined, SA),
	saveSkill: (slug: string, body: SkillDefinitionRequest) =>
		api.put<SkillDefinitionResponse>(`/superadmin/registry/skills/${slug}`, body, SA),

	// Registry — tools
	listTools: () =>
		api.get<ToolDefinitionResponse[]>('/superadmin/registry/tools', undefined, SA),
	saveTool: (slug: string, body: ToolDefinitionRequest) =>
		api.put<ToolDefinitionResponse>(`/superadmin/registry/tools/${slug}`, body, SA),

	// Email templates
	listTemplates: () =>
		api.get<EmailTemplateResponse[]>('/superadmin/email-templates', undefined, SA),
	getTemplate: (slug: string) =>
		api.get<EmailTemplateResponse>(`/superadmin/email-templates/${slug}`, undefined, SA),
	saveTemplate: (slug: string, body: EmailTemplateRequest) =>
		api.put<EmailTemplateResponse>(`/superadmin/email-templates/${slug}`, body, SA),

	// System settings
	getSettings: () => api.get<SystemSettingsResponse>('/superadmin/system-settings', undefined, SA),
	updateSettings: (body: SystemSettingsUpdateRequest) =>
		api.patch<SystemSettingsResponse>('/superadmin/system-settings', body, SA),

	// Tenant members
	listTenantMembers: (tenantId: string) =>
		api.get<TenantMemberResponse[]>(`/superadmin/tenants/${tenantId}/members`, undefined, SA),
	addTenantMember: (tenantId: string, body: { email: string; role: string }) =>
		api.post<TenantMemberResponse>(`/superadmin/tenants/${tenantId}/members`, body, SA),
	updateTenantMember: (tenantId: string, userId: string, body: { role?: string; status?: string }) =>
		api.patch<TenantMemberResponse>(`/superadmin/tenants/${tenantId}/members/${userId}`, body, SA),
	removeTenantMember: (tenantId: string, userId: string) =>
		api.del<MessageResponse>(`/superadmin/tenants/${tenantId}/members/${userId}`, SA),

	// Tenant instances
	listTenantInstances: (tenantId: string) =>
		api.get<SuperadminAgentInstanceResponse[]>(`/superadmin/tenants/${tenantId}/instances`, undefined, SA),

	// Tenant audit logs
	listTenantAudit: (tenantId: string) =>
		api.get<SuperadminAuditLogResponse[]>(`/superadmin/tenants/${tenantId}/audit`, undefined, SA),

	// Registry delete
	deleteSkill: (slug: string) =>
		api.del<MessageResponse>(`/superadmin/registry/skills/${slug}`, SA),
	deleteTool: (slug: string) =>
		api.del<MessageResponse>(`/superadmin/registry/tools/${slug}`, SA)
};
