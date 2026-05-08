<script lang="ts">
	import JsonConfigPanel from '$lib/components/JsonConfigPanel.svelte';
	import { registryApi } from '$lib/api/registry';
	import { getErrorMessage } from '$lib/api/client';
	import type { CredentialResponse } from '$lib/api/types';
	import KeyRound from '@lucide/svelte/icons/key-round';
	import Pencil from '@lucide/svelte/icons/pencil';
	import X from '@lucide/svelte/icons/x';
	import { toast } from 'svelte-sonner';

	let { data } = $props();

	let credentials = $state<CredentialResponse[]>(data.credentials);
	let editing = $state<CredentialResponse | null>(null);
	let secretRef = $state('');
	let metadataText = $state('{}');
	let saving = $state(false);

	function maskSecret(ref: string): string {
		if (!ref) return 'Not set';
		if (ref.length <= 4) return '****';
		return `****${ref.slice(-4)}`;
	}

	function startEdit(credential: CredentialResponse) {
		editing = credential;
		secretRef = credential.secret_ref;
		metadataText = JSON.stringify(credential.metadata ?? {}, null, 2);
	}

	function closeEdit() {
		editing = null;
		secretRef = '';
		metadataText = '{}';
	}

	async function saveCredential(json: string) {
		if (!editing) return;
		saving = true;
		try {
			const saved = await registryApi.saveCredential(editing.skill_slug, {
				secret_ref: secretRef.trim(),
				metadata: JSON.parse(json || '{}') as Record<string, unknown>
			});
			credentials = credentials.map((credential) =>
				credential.skill_slug === saved.skill_slug ? saved : credential
			);
			toast.success('Credential reference updated.');
			closeEdit();
		} catch (err) {
			toast.error(getErrorMessage(err, 'Credential update failed.'));
			throw err;
		} finally {
			saving = false;
		}
	}
</script>

<div class="mx-auto max-w-5xl space-y-6 p-6">
	<div class="flex items-center justify-between gap-4">
		<div>
			<h1 class="font-display text-xl font-semibold" style="color:var(--text-main)">Credential References</h1>
			<p class="mt-1 text-sm text-muted-foreground">Tenant credential references by skill slug</p>
		</div>
		<div class="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
			<KeyRound class="h-5 w-5" />
		</div>
	</div>

	<section class="rounded-xl" style="background:var(--surface);border:1px solid var(--ds-border)">
		{#if credentials.length === 0}
			<p class="py-12 text-center text-sm text-muted-foreground">No credential references configured.</p>
		{:else}
			<div class="overflow-x-auto">
				<table class="w-full text-left text-sm">
					<thead class="border-b text-xs uppercase tracking-widest text-muted-foreground" style="border-color:var(--ds-border)">
						<tr>
							<th class="px-4 py-3 font-semibold">Skill</th>
							<th class="px-4 py-3 font-semibold">Secret ref</th>
							<th class="px-4 py-3 font-semibold">Metadata</th>
							<th class="px-4 py-3 text-right font-semibold">Actions</th>
						</tr>
					</thead>
					<tbody>
						{#each credentials as credential (credential.skill_slug)}
							<tr class="border-b last:border-b-0" style="border-color:var(--ds-border)">
								<td class="px-4 py-3 font-mono text-xs" style="color:var(--text-main)">{credential.skill_slug}</td>
								<td class="px-4 py-3 font-mono text-xs text-muted-foreground">{maskSecret(credential.secret_ref)}</td>
								<td class="max-w-md px-4 py-3">
									<pre class="max-h-24 overflow-auto rounded-lg p-2 text-xs text-muted-foreground" style="background:var(--surface-hover)">{JSON.stringify(credential.metadata ?? {}, null, 2)}</pre>
								</td>
								<td class="px-4 py-3 text-right">
									<button
										onclick={() => startEdit(credential)}
										class="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-blue-400 transition-colors hover:bg-blue-400/10"
									>
										<Pencil class="h-3.5 w-3.5" />
										Edit
									</button>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</section>

	{#if editing}
		<div class="rounded-xl p-6" style="background:var(--surface);border:1px solid var(--ds-border)">
			<div class="mb-4 flex items-center justify-between gap-4">
				<div>
					<h2 class="font-display text-sm font-semibold" style="color:var(--text-main)">Edit {editing.skill_slug}</h2>
					<p class="mt-0.5 text-xs text-muted-foreground">Secret value is stored outside the application; save only the reference.</p>
				</div>
				<button onclick={closeEdit} class="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-white/5 hover:text-foreground">
					<X class="h-4 w-4" />
				</button>
			</div>

			<div class="mb-4 space-y-1.5">
				<label class="block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Secret reference</label>
				<input type="password" bind:value={secretRef} class="auth-input w-full rounded-lg px-3.5 py-2.5 font-mono text-sm" />
			</div>

			<JsonConfigPanel value={metadataText} onSave={saveCredential} />
			{#if saving}
				<p class="mt-2 text-xs text-muted-foreground">Saving credential reference...</p>
			{/if}
		</div>
	{/if}
</div>
