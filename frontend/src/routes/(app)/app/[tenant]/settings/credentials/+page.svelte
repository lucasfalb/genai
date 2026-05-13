<script lang="ts">
	import JsonConfigPanel from '$lib/components/JsonConfigPanel.svelte';
	import { registryApi } from '$lib/api/registry';
	import { getErrorMessage } from '$lib/api/client';
	import type { CredentialResponse } from '$lib/api/types';
	import KeyRound from '@lucide/svelte/icons/key-round';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Search from '@lucide/svelte/icons/search';
	import X from '@lucide/svelte/icons/x';
	import { toast } from 'svelte-sonner';
	import * as Table from '$lib/components/ui/table';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Label } from '$lib/components/ui/label';

	let { data } = $props();

	let credentials = $state<CredentialResponse[]>(data.credentials);
	let editTarget = $state<CredentialResponse | null>(null);
	let secretRef = $state('');
	let metadataText = $state('{}');
	let saving = $state(false);
	let searchQuery = $state('');

	const filteredCredentials = $derived(
		credentials.filter((c) => c.skill_slug.toLowerCase().includes(searchQuery.toLowerCase()))
	);

	function maskSecret(ref: string): string {
		if (!ref) return 'Not set';
		if (ref.length <= 4) return '****';
		return `****${ref.slice(-4)}`;
	}

	function startEdit(credential: CredentialResponse) {
		editTarget = credential;
		secretRef = credential.secret_ref;
		metadataText = JSON.stringify(credential.metadata ?? {}, null, 2);
	}

	function closeEdit() {
		editTarget = null;
		secretRef = '';
		metadataText = '{}';
	}

	async function saveCredential(json: string) {
		if (!editTarget) return;
		saving = true;
		try {
			const saved = await registryApi.saveCredential(editTarget.skill_slug, {
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

<div class="flex flex-col gap-4 p-4">
	<!-- Search Row -->
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div class="relative w-full max-w-xs">
			<Search class="absolute top-2.5 left-2.5 h-4 w-4 text-muted-foreground" />
			<Input
				placeholder="Search skills..."
				bind:value={searchQuery}
				class="h-9 bg-background pl-9"
			/>
		</div>
	</div>

	<!-- Credentials Table -->
	<div class="overflow-hidden border bg-card">
		<Table.Root containerClass="scrollbar-none bg-card" class="w-full table-fixed">
			<Table.Header class="bg-background">
				<Table.Row class="bg-background hover:bg-background">
					<Table.Head class="w-[200px] bg-background py-2 text-[11px] font-bold tracking-wider uppercase">Skill</Table.Head>
					<Table.Head class="bg-background py-2 text-[11px] font-bold tracking-wider uppercase">Secret Reference</Table.Head>
					<Table.Head class="hidden bg-background py-2 text-[11px] font-bold tracking-wider uppercase md:table-cell">Metadata</Table.Head>
					<Table.Head class="w-[100px] bg-background py-2 text-right"></Table.Head>
				</Table.Row>
			</Table.Header>

			<Table.Body>
				{#if filteredCredentials.length === 0}
					<Table.Row class="bg-card hover:bg-card">
						<Table.Cell colspan={4} class="h-32 text-center text-muted-foreground">
							<div class="flex flex-col items-center gap-1">
								<span class="text-sm font-medium text-foreground">No credentials found</span>
								<span class="text-xs">Try adjusting your search query.</span>
							</div>
						</Table.Cell>
					</Table.Row>
				{:else}
					{#each filteredCredentials as credential (credential.skill_slug)}
						<Table.Row class="group bg-card transition-colors hover:bg-muted/30">
							<Table.Cell class="py-3">
								<div class="flex items-center gap-3 overflow-hidden">
									<div class="flex h-8 w-8 shrink-0 items-center justify-center border bg-background text-blue-400 transition-all group-hover:border-primary/40">
										<KeyRound class="h-4 w-4" />
									</div>
									<span class="truncate font-mono text-xs font-semibold">{credential.skill_slug}</span>
								</div>
							</Table.Cell>

							<Table.Cell class="py-3 font-mono text-xs text-muted-foreground">
								{maskSecret(credential.secret_ref)}
							</Table.Cell>

							<Table.Cell class="hidden py-3 md:table-cell">
								<div class="max-w-md">
									<pre class="line-clamp-1 truncate rounded bg-muted/50 px-2 py-1 text-[10px] text-muted-foreground">{JSON.stringify(credential.metadata ?? {})}</pre>
								</div>
							</Table.Cell>

							<Table.Cell class="py-3 text-right">
								<Button
									variant="ghost"
									size="sm"
									onclick={() => startEdit(credential)}
									class="h-8 gap-1.5 text-xs text-blue-400 hover:bg-blue-400/10 hover:text-blue-400"
								>
									<Pencil class="h-3.5 w-3.5" />
									Edit
								</Button>
							</Table.Cell>
						</Table.Row>
					{/each}
				{/if}
			</Table.Body>
		</Table.Root>
		<div class="border-t bg-card px-4 py-2">
			<p class="text-[10px] font-bold tracking-widest text-muted-foreground uppercase">
				Showing {filteredCredentials.length} of {credentials.length} skills
			</p>
		</div>
	</div>
</div>

<!-- Edit Dialog -->
<Dialog.Root open={!!editTarget} onOpenChange={(o) => { if (!o) closeEdit(); }}>
	<Dialog.Content class="sm:max-w-[600px]">
		<Dialog.Header>
			<Dialog.Title>Edit Credential Reference</Dialog.Title>
			<Dialog.Description>
				Update the secret reference and metadata for <strong class="text-foreground">{editTarget?.skill_slug}</strong>.
			</Dialog.Description>
		</Dialog.Header>

		<div class="grid gap-4 py-4">
			<div class="grid gap-2">
				<Label for="secret">Secret Reference</Label>
				<Input id="secret" type="password" bind:value={secretRef} placeholder="Environment variable name or key ID" />
				<p class="text-[10px] text-muted-foreground">The actual secret value is managed in your secure environment.</p>
			</div>
			
			<div class="grid gap-2">
				<Label>Metadata (JSON)</Label>
				<JsonConfigPanel value={metadataText} onSave={saveCredential} />
			</div>
		</div>

		<Dialog.Footer>
			<Button variant="outline" onclick={closeEdit}>Cancel</Button>
			{#if saving}
				<Button disabled><X class="mr-2 h-4 w-4 animate-spin" /> Saving...</Button>
			{:else}
				<p class="text-[10px] text-muted-foreground self-center italic">Metadata is saved via the code editor above.</p>
			{/if}
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<style>
	:global(td) {
		white-space: nowrap;
	}
</style>
