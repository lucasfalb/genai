<script lang="ts">
	let { role }: { role: string } = $props();

	const labels: Record<string, string> = {
		superadmin: 'Superadmin',
		tenant_admin: 'Tenant admin',
		owner: 'Owner',
		admin: 'Admin',
		member: 'Member',
		viewer: 'Viewer'
	};

	const classes: Record<string, string> = {
		superadmin: 'bg-purple-500/10 text-purple-400',
		tenant_admin: 'bg-blue-500/10 text-blue-400',
		owner: 'bg-purple-500/10 text-purple-400',
		admin: 'bg-blue-500/10 text-blue-400',
		member: 'bg-slate-500/10 text-slate-300',
		viewer: 'bg-cyan-500/10 text-cyan-300'
	};
</script>

<span class="rounded-full px-2 py-1 text-[10px] font-semibold uppercase {classes[role] ?? 'bg-white/5 text-muted-foreground'}">
	{labels[role] ?? role}
</span>
