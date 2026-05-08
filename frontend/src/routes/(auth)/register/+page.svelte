<script lang="ts">
	import User from '@lucide/svelte/icons/user';
	import Mail from '@lucide/svelte/icons/mail';
	import Lock from '@lucide/svelte/icons/lock';
	import UserPlus from '@lucide/svelte/icons/user-plus';

	let name = $state('');
	let email = $state('');
	let password = $state('');
	let confirm = $state('');
	let agreed = $state(false);
	let loading = $state(false);
	let error = $state('');

	import { goto } from '$app/navigation';
	import { authApi } from '$lib/api/auth';
	import { getErrorMessage } from '$lib/api/client';
	import { toast } from 'svelte-sonner';

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!name || !email || !password || !confirm) { error = 'Please fill in all fields.'; return; }
		if (password !== confirm) { error = 'Passwords do not match.'; return; }
		if (password.length < 8) { error = 'Password must be at least 8 characters.'; return; }
		if (!agreed) { error = 'You must accept the terms to continue.'; return; }
		error = '';
		loading = true;
		try {
			await authApi.register({ email, password, name });
			toast.success('Account created. Check your email to activate it.');
			await goto('/activation/pending?email=' + encodeURIComponent(email));
		} catch (err) {
			error = getErrorMessage(err, 'Registration failed. Please try again.');
			toast.error(error);
		} finally {
			loading = false;
		}
	}
</script>

<div class="mb-7">
	<h2 class="font-display text-2xl font-semibold tracking-tight" style="color:var(--text-main)">Create an account</h2>
	<p class="mt-1.5 text-sm text-muted-foreground">Fill in your details to get started.</p>
</div>

<div class="auth-card rounded-xl p-7">
	<form onsubmit={handleSubmit} class="flex flex-col gap-4">
		{#if error}
			<div class="rounded-lg px-3 py-2.5 text-xs font-medium text-red-500" style="background:color-mix(in srgb,red 8%,transparent);border:1px solid color-mix(in srgb,red 18%,transparent)">{error}</div>
		{/if}

		<div class="flex flex-col gap-1.5">
			<label class="font-display block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Full name</label>
			<div class="relative">
				<User class="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/50" />
				<input type="text" bind:value={name} placeholder="Your name" autocomplete="name"
					class="auth-input rounded-lg py-2.5 pr-4 pl-9 text-sm" />
			</div>
		</div>

		<div class="flex flex-col gap-1.5">
			<label class="font-display block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Email</label>
			<div class="relative">
				<Mail class="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/50" />
				<input type="email" bind:value={email} placeholder="you@example.com" autocomplete="email"
					class="auth-input rounded-lg py-2.5 pr-4 pl-9 text-sm" />
			</div>
		</div>

		<div class="grid grid-cols-2 gap-3">
			<div class="flex flex-col gap-1.5">
				<label class="font-display block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Password</label>
				<div class="relative">
					<Lock class="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/50" />
					<input type="password" bind:value={password} placeholder="Min. 8 chars" autocomplete="new-password"
						class="auth-input rounded-lg py-2.5 pr-3 pl-9 text-sm" />
				</div>
			</div>
			<div class="flex flex-col gap-1.5">
				<label class="font-display block text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Confirm</label>
				<div class="relative">
					<Lock class="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/50" />
					<input type="password" bind:value={confirm} placeholder="Repeat" autocomplete="new-password"
						class="auth-input rounded-lg py-2.5 pr-3 pl-9 text-sm" />
				</div>
			</div>
		</div>

		<label class="flex cursor-pointer items-start gap-2 pt-0.5">
			<input type="checkbox" bind:checked={agreed} class="mt-0.5 h-4 w-4 shrink-0 rounded accent-blue-500" />
			<span class="text-xs leading-relaxed text-muted-foreground">
				I agree to the <a href="#" class="text-blue-500 hover:text-blue-400">Terms of Service</a> and
				<a href="#" class="text-blue-500 hover:text-blue-400">Privacy Policy</a>
			</span>
		</label>

		<button type="submit" disabled={loading}
			class="auth-submit-btn flex w-full items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-semibold tracking-wide text-white transition-all active:scale-[0.98] disabled:opacity-60">
			<UserPlus class="h-4 w-4" />
			{loading ? 'Creating account...' : 'Create account'}
		</button>
	</form>
</div>

<p class="mt-5 text-center text-sm text-muted-foreground">
	Already have an account?
	<a href="/login" class="font-semibold text-blue-500 transition-colors hover:text-blue-400">Sign in</a>
</p>
