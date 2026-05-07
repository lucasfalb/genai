from enum import StrEnum


class Role(StrEnum):
    SUPERADMIN = "superadmin"
    TENANT_ADMIN = "tenant_admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Permission(StrEnum):
    MANAGE_GLOBAL_USERS = "manage_global_users"
    MANAGE_AGENT_INSTANCES = "manage_agent_instances"
    MANAGE_SKILLS_TOOLS = "manage_skills_tools"
    MANAGE_HANDOFFS = "manage_handoffs"
    CONFIGURE_CHANNELS = "configure_channels"
    UPLOAD_RAG_DOCUMENTS = "upload_rag_documents"
    INVITE_MEMBERS = "invite_members"
    VIEW_LOGS = "view_logs"
    INTERACT_WITH_AGENTS = "interact_with_agents"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.SUPERADMIN: set(Permission),
    Role.TENANT_ADMIN: {
        Permission.MANAGE_AGENT_INSTANCES,
        Permission.MANAGE_SKILLS_TOOLS,
        Permission.MANAGE_HANDOFFS,
        Permission.CONFIGURE_CHANNELS,
        Permission.UPLOAD_RAG_DOCUMENTS,
        Permission.INVITE_MEMBERS,
        Permission.VIEW_LOGS,
        Permission.INTERACT_WITH_AGENTS,
    },
    Role.MEMBER: {
        Permission.CONFIGURE_CHANNELS,
        Permission.UPLOAD_RAG_DOCUMENTS,
        Permission.VIEW_LOGS,
        Permission.INTERACT_WITH_AGENTS,
    },
    Role.VIEWER: {
        Permission.VIEW_LOGS,
        Permission.INTERACT_WITH_AGENTS,
    },
}


def has_permission(role: str, permission: Permission) -> bool:
    try:
        parsed_role = Role(role)
    except ValueError:
        return False
    return permission in ROLE_PERMISSIONS[parsed_role]
