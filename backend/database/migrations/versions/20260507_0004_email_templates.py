"""email templates

Revision ID: 20260507_0004
Revises: 20260507_0003
Create Date: 2026-05-07
"""
from alembic import op

revision = "20260507_0004"
down_revision = "20260507_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE email_templates (
          id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          slug               TEXT UNIQUE NOT NULL,
          name               TEXT NOT NULL,
          description        TEXT,
          subject_template   TEXT NOT NULL,
          body_template      TEXT NOT NULL,
          body_format        TEXT NOT NULL DEFAULT 'html',
          variables_schema   JSONB NOT NULL DEFAULT '{}',
          is_active          BOOLEAN NOT NULL DEFAULT true,
          created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON email_templates TO genai_app")
    op.execute(
        """
        INSERT INTO email_templates
          (slug, name, description, subject_template, body_template, variables_schema)
        VALUES
          (
            'account_activation',
            'Ativacao de conta',
            'Enviado para confirmar o email e ativar a conta do usuario.',
            'Ative sua conta na {{ platform_name }}',
            '<p>Ola {{ user_name }},</p><p>Use o link abaixo para ativar sua conta:</p><p><a href="{{ activation_url }}">Ativar conta</a></p><p>Este link expira em {{ expires_in }}.</p>',
            '{"required":["platform_name","user_name","activation_url","expires_in"]}'::jsonb
          ),
          (
            'tenant_invitation',
            'Convite para tenant',
            'Enviado quando um usuario e convidado para participar de um tenant.',
            'Convite para acessar {{ tenant_name }}',
            '<p>Ola {{ invitee_email }},</p><p>{{ inviter_name }} convidou voce para acessar {{ tenant_name }} como {{ role }}.</p><p><a href="{{ invitation_url }}">Aceitar convite</a></p><p>Este convite expira em {{ expires_in }}.</p>',
            '{"required":["invitee_email","inviter_name","tenant_name","role","invitation_url","expires_in"]}'::jsonb
          ),
          (
            'password_reset',
            'Recuperacao de senha',
            'Enviado quando o usuario solicita recuperacao de senha.',
            'Redefina sua senha',
            '<p>Ola {{ user_name }},</p><p>Recebemos uma solicitacao para redefinir sua senha.</p><p><a href="{{ reset_url }}">Redefinir senha</a></p><p>Este link expira em {{ expires_in }}.</p>',
            '{"required":["user_name","reset_url","expires_in"]}'::jsonb
          ),
          (
            'password_changed',
            'Senha alterada',
            'Aviso de seguranca enviado apos alteracao de senha.',
            'Sua senha foi alterada',
            '<p>Ola {{ user_name }},</p><p>Sua senha foi alterada em {{ changed_at }}.</p><p>Se nao foi voce, entre em contato com o suporte imediatamente.</p>',
            '{"required":["user_name","changed_at"]}'::jsonb
          ),
          (
            'membership_assigned',
            'Acesso liberado',
            'Enviado quando o usuario recebe acesso ativo a um tenant.',
            'Seu acesso a {{ tenant_name }} foi liberado',
            '<p>Ola {{ user_name }},</p><p>Seu acesso a {{ tenant_name }} foi liberado com o papel {{ role }}.</p><p><a href="{{ login_url }}">Entrar</a></p>',
            '{"required":["user_name","tenant_name","role","login_url"]}'::jsonb
          )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS email_templates")
