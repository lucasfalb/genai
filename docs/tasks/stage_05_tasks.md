# Stage 05 Tasks - Base Multitenant Workflows

| ID | Task | Status | Priority | Depends On |
| :--- | :--- | :--- | :--- | :--- |
| TASK-025 | [Auth Token Tables e Email Event Outbox](task_025_auth_token_tables_email_event_outbox.md) | COMPLETED | CRITICAL | TASK-011 |
| TASK-026 | [Account Activation Flow](task_026_account_activation_flow.md) | COMPLETED | CRITICAL | TASK-025 |
| TASK-027 | [Password Recovery e Change Flow](task_027_password_recovery_change_flow.md) | COMPLETED | CRITICAL | TASK-025 |
| TASK-028 | [Auth Me Logout e Session Introspection](task_028_auth_me_logout_session_introspection.md) | COMPLETED | HIGH | TASK-008 |
| TASK-029 | [Superadmin Tenant e User Administration](task_029_superadmin_tenant_user_administration.md) | COMPLETED | CRITICAL | TASK-012 |
| TASK-030 | [Tenant Members e RBAC Administration](task_030_tenant_members_rbac_administration.md) | COMPLETED | CRITICAL | TASK-010, TASK-012 |
| TASK-031 | [Tenant Invitation Lifecycle](task_031_tenant_invitation_lifecycle.md) | COMPLETED | CRITICAL | TASK-025, TASK-030 |
| TASK-032 | [Tenant Agent Instance CRUD](task_032_tenant_agent_instance_crud.md) | COMPLETED | CRITICAL | TASK-015, TASK-030 |
| TASK-033 | [Workflow Audit Versions e Cache Invalidation](task_033_workflow_audit_versions_cache_invalidation.md) | COMPLETED | HIGH | TASK-029, TASK-030, TASK-031, TASK-032 |
| TASK-034 | [Stage 05 API Bruno e Workflow Verification](task_034_stage_05_api_bruno_workflow_verification.md) | PENDING | HIGH | TASK-026, TASK-027, TASK-028, TASK-029, TASK-030, TASK-031, TASK-032, TASK-033 |
| TASK-035 | [API Response Envelope Standard](task_035_api_response_envelope_standard.md) | COMPLETED | HIGH | TASK-026 |
| TASK-036 | [SystemPrompt Schema e PromptCache](task_036_system_prompt_schema_prompt_cache.md) | COMPLETED | CRITICAL | TASK-019, TASK-020 |
| TASK-037 | [PromptBuilder — Montagem Sanduiche](task_037_prompt_builder_sandwich_assembly.md) | COMPLETED | CRITICAL | TASK-015, TASK-036 |
| TASK-038 | [PromptSanitizer - Validacao e Densidade](task_038_prompt_sanitizer_validation_density.md) | COMPLETED | HIGH | TASK-037 |
| TASK-039 | [LLM Node e Provider Integration](task_039_llm_node_provider_integration.md) | COMPLETED | CRITICAL | TASK-037, TASK-023, TASK-061, TASK-062 |
| TASK-040 | [Prompt Cache Invalidation em Mutacoes de Instancia](task_040_prompt_cache_invalidation_admin_mutations.md) | COMPLETED | HIGH | TASK-036, TASK-032 |
| TASK-061 | [AI Provider Config por Tenant e Plataforma](task_061_ai_provider_config.md) | COMPLETED | HIGH | TASK-032, TASK-036 |
| TASK-062 | [System Settings e Tenant AI Config Consolidation](task_062_system_settings_tenant_ai_config_consolidation.md) | COMPLETED | CRITICAL | TASK-029, TASK-032, TASK-039, TASK-061 |
| TASK-063 | [I18n Platform Messages e Locale Settings](task_063_i18n_platform_messages_locale_settings.md) | PENDING | HIGH | TASK-062 |
| TASK-064 | [Agent Guardrails Customizados e Instrucoes por Topicos](task_064_agent_guardrails_customizados_instrucoes_por_topicos.md) | PENDING | CRITICAL | TASK-032, TASK-036, TASK-037, TASK-038 |

## Scope

Estas tasks cobrem o Stage 05 definido em `docs/stages/stage_05_base_multitenant_workflows.md` e `docs/stages/stage_05_prompts.md`: completar os workflows base de autenticacao, tenants, membros, convites, instancias, auditoria/versionamento, contratos Bruno/OpenAPI e runtime de prompt sanduiche.

## Implementation Order

1. Criar tabelas auxiliares de tokens transacionais e email outbox.
2. Fechar account activation e password lifecycle.
3. Expor introspeccao de auth e logout.
4. Implementar administracao superadmin de tenants/users.
5. Implementar members/RBAC e invitations por tenant.
6. Implementar CRUD tenant-scoped de instancias.
7. Garantir audit/version/cache para todas as mutacoes.
8. Validar OpenAPI, Bruno e testes end-to-end.
9. Consolidar configuracoes operacionais globais em `system_settings` e configuracao AI por tenant em `tenants`.
10. Planejar i18n para mensagens da plataforma, templates e preferencias de locale.
11. Evoluir o agente base para aceitar guardrails customizados e instrucoes estruturadas por topicos.

## Notes

- Superadmin controla qualquer tenant sem membership visivel.
- Listagem de membros deve consultar `memberships` e excluir `users.is_superadmin = true`.
- Toda rota tenant-scoped exige Bearer token, `X-Tenant-ID` e RBAC.
- Toda rota criada neste stage deve ganhar request correspondente em `genai-endpoints/`.
- Toda rota JSON deve retornar envelope padrao `ApiResponse` em sucesso e envelope `ApiErrorResponse` em erro.
- Configuracoes globais da plataforma devem viver em `system_settings`; configuracao AI especifica do tenant deve viver em colunas de `tenants`, nao em tabelas paralelas.
- `system_settings` deve combinar colunas tipadas para settings criticos com `custom_settings/public_settings` JSONB para extensibilidade controlada pelo superadmin.
- `platform_public_url` deve permanecer como origem publica do frontend para geracao de links absolutos; `platform_logo_url` deve ser exposto como branding publico seguro.
- Agentes devem suportar instrucoes por topico e guardrails customizados por tenant/instancia, com validacao antes de entrar no prompt final.
