<script lang="ts">
	import { collectionsApi } from '$lib/api/collections';
	import { getErrorMessage } from '$lib/api/client';
	import type { CollectionResponse } from '$lib/api/types';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { toast } from 'svelte-sonner';

	let {
		open = $bindable(false),
		mode,
		collection = null,
		onSaved
	} = $props<{
		open: boolean;
		mode: 'create' | 'edit';
		collection?: CollectionResponse | null;
		onSaved: (collection: CollectionResponse) => void;
	}>();

	let name = $state(collection?.name ?? '');
	let description = $state(collection?.description ?? '');
	let saving = $state(false);

	$effect(() => {
		if (open) {
			name = collection?.name ?? '';
			description = collection?.description ?? '';
		}
	});

	async function save() {
		if (name.trim().length < 2) {
			toast.error('Collection name must have at least 2 characters.');
			return;
		}
		saving = true;
		try {
			const saved =
				mode === 'edit' && collection
					? await collectionsApi.update(collection.id, {
							name: name.trim(),
							description: description.trim() || undefined
						})
					: await collectionsApi.create({
							name: name.trim(),
							description: description.trim() || undefined
						});
			onSaved(saved);
			open = false;
			toast.success(mode === 'edit' ? 'Collection updated.' : 'Collection created.');
		} catch (err) {
			toast.error(getErrorMessage(err, 'Collection save failed.'));
		} finally {
			saving = false;
		}
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-lg">
		<Dialog.Header>
			<Dialog.Title>{mode === 'edit' ? 'Edit Collection' : 'New Collection'}</Dialog.Title>
			<Dialog.Description>Collections group documents used by agent knowledge retrieval.</Dialog.Description>
		</Dialog.Header>
		<div class="space-y-4">
			<div class="space-y-1.5">
				<label for="collection-name" class="text-sm font-medium">Name</label>
				<input
					id="collection-name"
					bind:value={name}
					class="auth-input w-full rounded-lg px-3 py-2 text-sm"
					placeholder="Product docs"
				/>
			</div>
			<div class="space-y-1.5">
				<label for="collection-description" class="text-sm font-medium">Description</label>
				<textarea
					id="collection-description"
					bind:value={description}
					rows="4"
					class="auth-input w-full resize-y rounded-lg px-3 py-2 text-sm"
					placeholder="Optional description"
				></textarea>
			</div>
		</div>
		<Dialog.Footer>
			<Button variant="ghost" onclick={() => (open = false)}>Cancel</Button>
			<Button disabled={saving} onclick={save}>{saving ? 'Saving...' : 'Save'}</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
