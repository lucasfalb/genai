<script lang="ts">
	import * as Accordion from '$lib/components/ui/accordion/index.js';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import * as Avatar from '$lib/components/ui/avatar/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as ButtonGroup from '$lib/components/ui/button-group/index.js';
	import * as Breadcrumb from '$lib/components/ui/breadcrumb/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import * as Collapsible from '$lib/components/ui/collapsible/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Empty from '$lib/components/ui/empty/index.js';
	import * as Field from '$lib/components/ui/field/index.js';
	import * as HoverCard from '$lib/components/ui/hover-card/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Kbd, KbdGroup } from '$lib/components/ui/kbd/index.js';
	import { Label } from '$lib/components/ui/label/index.js';

	import * as Popover from '$lib/components/ui/popover/index.js';
	import { Progress } from '$lib/components/ui/progress/index.js';
	import * as RadioGroup from '$lib/components/ui/radio-group/index.js';
	import * as ScrollArea from '$lib/components/ui/scroll-area/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import * as Sheet from '$lib/components/ui/sheet/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { Slider } from '$lib/components/ui/slider/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import { Toggle } from '$lib/components/ui/toggle/index.js';
	import * as ToggleGroup from '$lib/components/ui/toggle-group/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';

	import AlertCircle from '@lucide/svelte/icons/alert-circle';
	import AlignCenter from '@lucide/svelte/icons/align-center';
	import AlignLeft from '@lucide/svelte/icons/align-left';
	import AlignRight from '@lucide/svelte/icons/align-right';
	import Bold from '@lucide/svelte/icons/bold';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Database from '@lucide/svelte/icons/database';
	import Info from '@lucide/svelte/icons/info';
	import Italic from '@lucide/svelte/icons/italic';
	import Plus from '@lucide/svelte/icons/plus';
	import Search from '@lucide/svelte/icons/search';
	import Settings from '@lucide/svelte/icons/settings';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Underline from '@lucide/svelte/icons/underline';

	let switchVal = $state(false);
	let checkVal = $state(false);
	let sliderVal = $state(40);
	let radioVal = $state('gpt4');
	let toggleGroupVal = $state('left');
	let dialogOpen = $state(false);
	let alertDialogOpen = $state(false);
	let sheetOpen = $state(false);
	let collapsibleOpen = $state(false);
	let selectVal = $state('');

	const tableRows = [
		{
			id: '#4a9c8f',
			engine: 'GPT-4 Turbo',
			status: 'Active',
			region: 'us-east-1',
			latency: '89ms'
		},
		{
			id: '#7f3d22',
			engine: 'Claude 3 Opus',
			status: 'Active',
			region: 'us-west-2',
			latency: '145ms'
		},
		{
			id: '#8v1p00',
			engine: 'Claude 3 Opus',
			status: 'Stopped',
			region: 'eu-central-1',
			latency: '—'
		}
	];

	function statusClass(s: string) {
		if (s === 'Active') return 'border-emerald-500/20 bg-emerald-500/10 text-emerald-500';
		return 'border-slate-500/20 bg-slate-500/10 text-slate-400';
	}
</script>

{#snippet sec(n: string, title: string)}
	<div class="mb-6">
		<div class="mb-3 flex items-center gap-3">
			<span class="font-mono text-[10px] text-blue-500/70">{n}</span>
			<h2
				class="font-display text-xs font-semibold tracking-[0.15em] uppercase"
				style="color:var(--text-muted)"
			>
				{title}
			</h2>
		</div>
		<Separator />
	</div>
{/snippet}

{#snippet sub(label: string)}
	<p class="mb-2 text-[10px] font-medium tracking-widest text-muted-foreground uppercase">
		{label}
	</p>
{/snippet}

<div class="max-w-4xl space-y-14 p-8">
	<!-- 01 BUTTONS -->
	<section>
		{@render sec('01', 'Buttons & Actions')}
		<div class="space-y-6">
			{@render sub('Variants')}
			<div class="flex flex-wrap gap-2">
				<Button>Default</Button>
				<Button variant="outline">Outline</Button>
				<Button variant="secondary">Secondary</Button>
				<Button variant="ghost">Ghost</Button>
				<Button variant="destructive">Destructive</Button>
				<Button variant="link">Link</Button>
			</div>

			{@render sub('Sizes')}
			<div class="flex flex-wrap items-center gap-2">
				<Button size="xs">X-Small</Button>
				<Button size="sm">Small</Button>
				<Button>Default</Button>
				<Button size="lg">Large</Button>
			</div>

			{@render sub('With Icons')}
			<div class="flex flex-wrap items-center gap-2">
				<Button><Plus data-icon="inline-start" />New Instance</Button>
				<Button variant="outline"><Search data-icon="inline-start" />Search</Button>
				<Button variant="ghost" size="icon"><Settings /></Button>
				<Button variant="ghost" size="icon-sm"><Trash2 /></Button>
				<Button variant="destructive" size="icon"><Trash2 /></Button>
			</div>

			{@render sub('States')}
			<div class="flex items-center gap-2">
				<Button disabled>Disabled</Button>
				<Button variant="outline" disabled>Disabled Outline</Button>
				<Button><Spinner class="size-3" />&nbsp;Loading</Button>
			</div>

			{@render sub('Button Group')}
			<ButtonGroup.Root>
				<Button variant="outline"><AlignLeft /></Button>
				<Button variant="outline"><AlignCenter /></Button>
				<Button variant="outline"><AlignRight /></Button>
			</ButtonGroup.Root>
		</div>
	</section>

	<!-- 02 BADGES & KBD -->
	<section>
		{@render sec('02', 'Badges & Labels')}
		<div class="space-y-6">
			{@render sub('Badge Variants')}
			<div class="flex flex-wrap gap-2">
				<Badge>Default</Badge>
				<Badge variant="secondary">Secondary</Badge>
				<Badge variant="outline">Outline</Badge>
				<Badge variant="destructive">Destructive</Badge>
				<Badge variant="ghost">Ghost</Badge>
			</div>

			{@render sub('Semantic Status Badges')}
			<div class="flex flex-wrap gap-2">
				<Badge class="border-emerald-500/20 bg-emerald-500/10 text-emerald-500">Active</Badge>
				<Badge class="border-blue-500/20 bg-blue-500/10 text-blue-500">Training</Badge>
				<Badge class="border-amber-500/20 bg-amber-500/10 text-amber-500">Pending</Badge>
				<Badge class="border-red-500/20 bg-red-500/10 text-red-400">Error</Badge>
				<Badge class="border-slate-500/20 bg-slate-500/10 text-slate-400">Stopped</Badge>
				<Badge class="border-violet-500/20 bg-violet-500/10 text-violet-400">Indexed</Badge>
			</div>

			{@render sub('Keyboard Shortcuts')}
			<div class="flex items-center gap-4">
				<KbdGroup><Kbd>⌘</Kbd><Kbd>K</Kbd></KbdGroup>
				<KbdGroup><Kbd>Ctrl</Kbd><Kbd>Shift</Kbd><Kbd>P</Kbd></KbdGroup>
				<KbdGroup><Kbd>↵</Kbd></KbdGroup>
				<KbdGroup><Kbd>Esc</Kbd></KbdGroup>
			</div>
		</div>
	</section>

	<!-- 03 FORM CONTROLS -->
	<section>
		{@render sec('03', 'Form Controls')}
		<div class="grid grid-cols-1 gap-8 md:grid-cols-2">
			<div class="space-y-6">
				{@render sub('Input')}
				<Field.Group>
					<Field.Field>
						<Field.Label>Instance Name</Field.Label>
						<Input placeholder="e.g. support-alpha-01" />
					</Field.Field>
					<Field.Field>
						<Field.Label>API Key</Field.Label>
						<Input type="password" placeholder="sk-..." />
						<Field.Description>Used for LLM provider authentication.</Field.Description>
					</Field.Field>
					<Field.Field>
						<Field.Label>Disabled</Field.Label>
						<Input disabled value="read-only-value" />
					</Field.Field>
				</Field.Group>

				{@render sub('Textarea')}
				<Textarea placeholder="Enter system prompt..." rows={4} />

				{@render sub('Select')}
				<Select.Root type="single" bind:value={selectVal}>
					<Select.Trigger class="w-full">
						{selectVal || 'Choose model...'}
					</Select.Trigger>
					<Select.Content>
						<Select.Group>
							<Select.GroupHeading>OpenAI</Select.GroupHeading>
							<Select.Item value="gpt4o" label="GPT-4o">GPT-4o</Select.Item>
							<Select.Item value="gpt4t" label="GPT-4 Turbo">GPT-4 Turbo</Select.Item>
						</Select.Group>
						<Select.Separator />
						<Select.Group>
							<Select.GroupHeading>Anthropic</Select.GroupHeading>
							<Select.Item value="claude-opus" label="Claude Opus 4.7">Claude Opus 4.7</Select.Item>
							<Select.Item value="claude-sonnet" label="Claude Sonnet 4.6"
								>Claude Sonnet 4.6</Select.Item
							>
						</Select.Group>
					</Select.Content>
				</Select.Root>
			</div>

			<div class="space-y-6">
				{@render sub('Checkbox & Switch')}
				<div class="space-y-3">
					<div class="flex items-center gap-2.5">
						<Checkbox bind:checked={checkVal} id="rag" />
						<Label for="rag">Enable RAG lookup</Label>
					</div>
					<div class="flex items-center gap-2.5">
						<Checkbox checked={true} id="web" />
						<Label for="web">Enable web search</Label>
					</div>
					<div class="flex items-center gap-2.5">
						<Checkbox disabled id="tools" />
						<Label for="tools" class="text-muted-foreground">Tools (unavailable)</Label>
					</div>
					<Separator />
					<div class="flex items-center justify-between">
						<Label for="sw1">Streaming mode</Label>
						<Switch bind:checked={switchVal} id="sw1" />
					</div>
					<div class="flex items-center justify-between">
						<Label for="sw2">Prompt caching</Label>
						<Switch checked={true} id="sw2" />
					</div>
				</div>

				{@render sub('Radio Group')}
				<RadioGroup.Root bind:value={radioVal} class="space-y-2">
					<div class="flex items-center gap-2.5">
						<RadioGroup.Item value="gpt4" id="r1" />
						<Label for="r1">GPT-4 Turbo</Label>
					</div>
					<div class="flex items-center gap-2.5">
						<RadioGroup.Item value="claude" id="r2" />
						<Label for="r2">Claude Sonnet 4.6</Label>
					</div>
					<div class="flex items-center gap-2.5">
						<RadioGroup.Item value="gemini" id="r3" />
						<Label for="r3">Gemini 1.5 Pro</Label>
					</div>
				</RadioGroup.Root>

				{@render sub('Toggle & Toggle Group')}
				<div class="space-y-3">
					<ToggleGroup.Root type="single" bind:value={toggleGroupVal} class="justify-start">
						<ToggleGroup.Item value="left"><AlignLeft /></ToggleGroup.Item>
						<ToggleGroup.Item value="center"><AlignCenter /></ToggleGroup.Item>
						<ToggleGroup.Item value="right"><AlignRight /></ToggleGroup.Item>
					</ToggleGroup.Root>
					<div class="flex gap-1">
						<Toggle><Bold /></Toggle>
						<Toggle><Italic /></Toggle>
						<Toggle><Underline /></Toggle>
					</div>
				</div>

				{@render sub('Slider')}
				<div class="space-y-2">
					<div class="flex justify-between text-xs">
						<span class="text-muted-foreground">Temperature</span>
						<span class="font-mono text-blue-400">{sliderVal}</span>
					</div>
					<Slider type="single" bind:value={sliderVal} min={0} max={100} step={1} />
				</div>
			</div>
		</div>
	</section>

	<!-- 04 FEEDBACK -->
	<section>
		{@render sec('04', 'Feedback & Status')}
		<div class="space-y-6">
			{@render sub('Alerts')}
			<div class="space-y-3">
				<Alert.Root>
					<Info class="size-4" />
					<Alert.Title>System notice</Alert.Title>
					<Alert.Description
						>New AI provider config propagates across all instances within 60 seconds of save.</Alert.Description
					>
				</Alert.Root>
				<Alert.Root variant="destructive">
					<AlertCircle class="size-4" />
					<Alert.Title>Instance error</Alert.Title>
					<Alert.Description
						>Instance #8v1p00 failed to initialize — missing OPENAI_API_KEY in tenant config.</Alert.Description
					>
				</Alert.Root>
			</div>

			{@render sub('Progress')}
			<div class="space-y-3">
				<div class="space-y-1.5">
					<div class="flex justify-between text-xs">
						<span class="text-muted-foreground">Token quota</span>
						<span class="font-mono">68%</span>
					</div>
					<Progress value={68} class="h-1.5" />
				</div>
				<div class="space-y-1.5">
					<div class="flex justify-between text-xs">
						<span class="text-muted-foreground">Vector index</span>
						<span class="font-mono text-emerald-500">91%</span>
					</div>
					<Progress value={91} class="h-1.5 [&>[data-slot=progress-indicator]]:bg-emerald-500" />
				</div>
				<div class="space-y-1.5">
					<div class="flex justify-between text-xs">
						<span class="text-muted-foreground">Memory pressure</span>
						<span class="font-mono text-amber-500">47%</span>
					</div>
					<Progress value={47} class="h-1.5 [&>[data-slot=progress-indicator]]:bg-amber-500" />
				</div>
			</div>

			{@render sub('Spinner')}
			<div class="flex items-center gap-5">
				<Spinner class="size-3" />
				<Spinner class="size-4" />
				<Spinner class="size-5" />
				<Spinner class="size-6 text-blue-500" />
				<Spinner class="size-7 text-emerald-500" />
			</div>

			{@render sub('Skeleton')}
			<div class="space-y-2.5">
				<Skeleton class="h-3.5 w-48" />
				<Skeleton class="h-3.5 w-64" />
				<Skeleton class="h-3.5 w-36" />
				<div class="flex gap-3 pt-2">
					<Skeleton class="size-9 shrink-0 rounded-full" />
					<div class="flex-1 space-y-2">
						<Skeleton class="h-3.5 w-32" />
						<Skeleton class="h-3 w-48" />
					</div>
				</div>
			</div>
		</div>
	</section>

	<!-- 05 NAVIGATION -->
	<section>
		{@render sec('05', 'Navigation')}
		<div class="space-y-6">
			{@render sub('Tabs')}
			<Tabs.Root value="instances">
				<Tabs.List>
					<Tabs.Trigger value="instances">Instances</Tabs.Trigger>
					<Tabs.Trigger value="skills">Skills</Tabs.Trigger>
					<Tabs.Trigger value="rag">RAG</Tabs.Trigger>
					<Tabs.Trigger value="handoff" disabled>Handoff</Tabs.Trigger>
				</Tabs.List>
				<Tabs.Content value="instances" class="mt-4">
					<p class="text-sm text-muted-foreground">Instance list renders here.</p>
				</Tabs.Content>
				<Tabs.Content value="skills" class="mt-4">
					<p class="text-sm text-muted-foreground">Skills registry renders here.</p>
				</Tabs.Content>
			</Tabs.Root>

			{@render sub('Breadcrumb')}
			<Breadcrumb.Root>
				<Breadcrumb.List>
					<Breadcrumb.Item>
						<Breadcrumb.Link href="/">Platform</Breadcrumb.Link>
					</Breadcrumb.Item>
					<Breadcrumb.Separator />
					<Breadcrumb.Item>
						<Breadcrumb.Link href="/registry">Registry</Breadcrumb.Link>
					</Breadcrumb.Item>
					<Breadcrumb.Separator />
					<Breadcrumb.Item>
						<Breadcrumb.Page>Instance #4a9c8f</Breadcrumb.Page>
					</Breadcrumb.Item>
				</Breadcrumb.List>
			</Breadcrumb.Root>

			{@render sub('Pagination')}
			<nav class="flex items-center gap-1">
				<Button variant="ghost" size="sm" class="gap-1.5">← Previous</Button>
				{#each [1, 2, 3] as p}
					<Button variant={p === 1 ? 'outline' : 'ghost'} size="icon" class="size-8 text-xs"
						>{p}</Button
					>
				{/each}
				<span class="px-1 text-xs text-muted-foreground">…</span>
				<Button variant="ghost" size="icon" class="size-8 text-xs">5</Button>
				<Button variant="ghost" size="sm" class="gap-1.5">Next →</Button>
			</nav>
		</div>
	</section>

	<!-- 06 DATA DISPLAY -->
	<section>
		{@render sec('06', 'Data Display')}
		<div class="space-y-6">
			{@render sub('Card')}
			<Card.Root>
				<Card.Header>
					<Card.Title>Instance Health</Card.Title>
					<Card.Description
						>Real-time metrics for agent instance #4a9c8f (GPT-4 Turbo · us-east-1)</Card.Description
					>
					<Card.Action>
						<Badge class="border-emerald-500/20 bg-emerald-500/10 text-emerald-500">Active</Badge>
					</Card.Action>
				</Card.Header>
				<Card.Content class="space-y-3">
					<div class="space-y-1.5">
						<div class="flex justify-between text-xs">
							<span class="text-muted-foreground">Latency</span>
							<span class="font-mono text-emerald-500">89ms</span>
						</div>
						<Progress value={22} class="h-1 [&>[data-slot=progress-indicator]]:bg-emerald-500" />
					</div>
					<div class="space-y-1.5">
						<div class="flex justify-between text-xs">
							<span class="text-muted-foreground">Token usage (24h)</span>
							<span class="font-mono">1.2M / 2M</span>
						</div>
						<Progress value={60} class="h-1" />
					</div>
				</Card.Content>
				<Card.Footer class="justify-between">
					<span class="text-xs text-muted-foreground">Last active 2 min ago</span>
					<Button variant="outline" size="sm">View logs</Button>
				</Card.Footer>
			</Card.Root>

			{@render sub('Avatar')}
			<div class="flex items-center gap-4">
				<Avatar.Root size="sm">
					<Avatar.Image src="" alt="LA" />
					<Avatar.Fallback>LA</Avatar.Fallback>
				</Avatar.Root>
				<Avatar.Root>
					<Avatar.Image src="" alt="AC" />
					<Avatar.Fallback>AC</Avatar.Fallback>
				</Avatar.Root>
				<Avatar.Root size="lg">
					<Avatar.Image src="" alt="PE" />
					<Avatar.Fallback>PE</Avatar.Fallback>
				</Avatar.Root>
				<Avatar.Group>
					<Avatar.Root><Avatar.Fallback>A</Avatar.Fallback></Avatar.Root>
					<Avatar.Root><Avatar.Fallback>B</Avatar.Fallback></Avatar.Root>
					<Avatar.Root><Avatar.Fallback>C</Avatar.Fallback></Avatar.Root>
					<Avatar.GroupCount>+4</Avatar.GroupCount>
				</Avatar.Group>
			</div>

			{@render sub('Table')}
			<Table.Root>
				<Table.Header>
					<Table.Row>
						<Table.Head>Instance</Table.Head>
						<Table.Head>Engine</Table.Head>
						<Table.Head>Status</Table.Head>
						<Table.Head>Region</Table.Head>
						<Table.Head class="text-right">Latency</Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body>
					{#each tableRows as row}
						<Table.Row>
							<Table.Cell class="font-mono text-xs">{row.id}</Table.Cell>
							<Table.Cell>{row.engine}</Table.Cell>
							<Table.Cell><Badge class={statusClass(row.status)}>{row.status}</Badge></Table.Cell>
							<Table.Cell class="text-muted-foreground">{row.region}</Table.Cell>
							<Table.Cell class="text-right font-mono text-xs">{row.latency}</Table.Cell>
						</Table.Row>
					{/each}
				</Table.Body>
			</Table.Root>
		</div>
	</section>

	<!-- 07 CONTAINERS -->
	<section>
		{@render sec('07', 'Containers')}
		<div class="grid grid-cols-1 gap-8 md:grid-cols-2">
			<div>
				{@render sub('Accordion')}
				<Accordion.Root type="single">
					<Accordion.Item value="q1">
						<Accordion.Trigger>What is an Agent Instance?</Accordion.Trigger>
						<Accordion.Content>
							<p class="text-sm text-muted-foreground">
								A configured deployment of the base agent with specific skills, tools, and RAG
								collections assigned per tenant.
							</p>
						</Accordion.Content>
					</Accordion.Item>
					<Accordion.Item value="q2">
						<Accordion.Trigger>How does prompt caching work?</Accordion.Trigger>
						<Accordion.Content>
							<p class="text-sm text-muted-foreground">
								The compiled system prompt is stored in Redis (TTL 600s). Instance config mutations
								automatically invalidate the cache.
							</p>
						</Accordion.Content>
					</Accordion.Item>
					<Accordion.Item value="q3">
						<Accordion.Trigger>What is a handoff route?</Accordion.Trigger>
						<Accordion.Content>
							<p class="text-sm text-muted-foreground">
								Inter-agent routing rules that transfer a session to a target instance when the
								trigger condition is matched.
							</p>
						</Accordion.Content>
					</Accordion.Item>
				</Accordion.Root>
			</div>

			<div class="space-y-4">
				{@render sub('Collapsible')}
				<Collapsible.Root bind:open={collapsibleOpen}>
					<div class="flex items-center justify-between">
						<span class="text-sm font-medium">Advanced settings</span>
						<Collapsible.Trigger>
							<Button variant="ghost" size="icon-sm">
								<ChevronDown
									class="size-4 transition-transform duration-200 {collapsibleOpen
										? 'rotate-180'
										: ''}"
								/>
							</Button>
						</Collapsible.Trigger>
					</div>
					<Collapsible.Content class="mt-3 space-y-2.5">
						<div class="flex items-center justify-between gap-4">
							<Label class="shrink-0 text-sm">Max tokens</Label>
							<Input class="w-28 text-right font-mono" value="4096" />
						</div>
						<div class="flex items-center justify-between gap-4">
							<Label class="shrink-0 text-sm">Timeout (s)</Label>
							<Input class="w-28 text-right font-mono" value="30" />
						</div>
						<div class="flex items-center justify-between gap-4">
							<Label class="shrink-0 text-sm">Temperature</Label>
							<Input class="w-28 text-right font-mono" value="0.7" />
						</div>
					</Collapsible.Content>
				</Collapsible.Root>

				{@render sub('Scroll Area')}
				<ScrollArea.Root class="h-36 border" style="border-color:var(--ds-border)">
					<div class="space-y-1.5 p-3">
						{#each Array.from({ length: 16 }, (_, i) => i) as i}
							<div class="flex items-center gap-3 text-xs">
								<span class="w-5 shrink-0 font-mono text-muted-foreground/60"
									>{String(i + 1).padStart(2, '0')}</span
								>
								<span class="text-muted-foreground"
									>Agent #4a9c8f processed request in {80 + i * 7}ms</span
								>
							</div>
						{/each}
					</div>
				</ScrollArea.Root>
			</div>
		</div>
	</section>

	<!-- 08 EMPTY STATE -->
	<section>
		{@render sec('08', 'Empty State')}
		<Empty.Root class="border" style="border-color:var(--ds-border)">
			<Empty.Media>
				<Database class="size-8 text-muted-foreground/40" />
			</Empty.Media>
			<Empty.Header>
				<Empty.Title>No collections yet</Empty.Title>
				<Empty.Description
					>Create your first RAG collection to enable knowledge-augmented responses for this tenant.</Empty.Description
				>
			</Empty.Header>
			<Empty.Content>
				<Button><Plus data-icon="inline-start" />New Collection</Button>
			</Empty.Content>
		</Empty.Root>
	</section>

	<!-- 09 OVERLAYS -->
	<section>
		{@render sec('09', 'Overlays & Popups')}
		<div class="flex flex-wrap gap-3">
			<!-- Dialog -->
			<Dialog.Root bind:open={dialogOpen}>
				<Dialog.Trigger>
					<Button variant="outline">Dialog</Button>
				</Dialog.Trigger>
				<Dialog.Content>
					<Dialog.Header>
						<Dialog.Title>Deploy New Instance</Dialog.Title>
						<Dialog.Description
							>Configure and deploy a new agent instance for this tenant.</Dialog.Description
						>
					</Dialog.Header>
					<div class="py-3">
						<Field.Group>
							<Field.Field>
								<Field.Label>Instance name</Field.Label>
								<Input placeholder="support-alpha-01" />
							</Field.Field>
						</Field.Group>
					</div>
					<Dialog.Footer>
						<Button variant="ghost" onclick={() => (dialogOpen = false)}>Cancel</Button>
						<Button onclick={() => (dialogOpen = false)}>Deploy</Button>
					</Dialog.Footer>
				</Dialog.Content>
			</Dialog.Root>

			<!-- AlertDialog -->
			<AlertDialog.Root bind:open={alertDialogOpen}>
				<AlertDialog.Trigger>
					<Button variant="destructive">Alert Dialog</Button>
				</AlertDialog.Trigger>
				<AlertDialog.Content>
					<AlertDialog.Header>
						<AlertDialog.Title>Delete instance #4a9c8f?</AlertDialog.Title>
						<AlertDialog.Description
							>This action cannot be undone. All sessions and audit logs will be permanently
							deleted.</AlertDialog.Description
						>
					</AlertDialog.Header>
					<AlertDialog.Footer>
						<AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
						<AlertDialog.Action>Delete permanently</AlertDialog.Action>
					</AlertDialog.Footer>
				</AlertDialog.Content>
			</AlertDialog.Root>

			<!-- Sheet -->
			<Sheet.Root bind:open={sheetOpen}>
				<Sheet.Trigger>
					<Button variant="outline">Sheet</Button>
				</Sheet.Trigger>
				<Sheet.Content>
					<Sheet.Header>
						<Sheet.Title>Instance Configuration</Sheet.Title>
						<Sheet.Description>Edit settings for instance #4a9c8f</Sheet.Description>
					</Sheet.Header>
					<div class="space-y-4 p-6">
						<Field.Group>
							<Field.Field>
								<Field.Label>System prompt</Field.Label>
								<Textarea rows={6} placeholder="You are a helpful assistant..." />
							</Field.Field>
						</Field.Group>
					</div>
					<Sheet.Footer>
						<Button variant="ghost" onclick={() => (sheetOpen = false)}>Cancel</Button>
						<Button onclick={() => (sheetOpen = false)}>Save changes</Button>
					</Sheet.Footer>
				</Sheet.Content>
			</Sheet.Root>

			<!-- Popover -->
			<Popover.Root>
				<Popover.Trigger>
					<Button variant="outline">Popover</Button>
				</Popover.Trigger>
				<Popover.Content class="w-60">
					<div class="space-y-3">
						<p class="text-sm font-medium">Filter instances</p>
						<Input placeholder="Search by ID or engine..." />
						<div class="flex gap-2">
							<Button size="sm" class="flex-1">Apply</Button>
							<Button size="sm" variant="ghost" class="flex-1">Reset</Button>
						</div>
					</div>
				</Popover.Content>
			</Popover.Root>

			<!-- Tooltip -->
			<Tooltip.Provider>
				<Tooltip.Root>
					<Tooltip.Trigger>
						<Button variant="ghost" size="icon"><Info class="size-4" /></Button>
					</Tooltip.Trigger>
					<Tooltip.Content>
						<p>Instance token usage last 24h</p>
					</Tooltip.Content>
				</Tooltip.Root>
			</Tooltip.Provider>

			<!-- HoverCard -->
			<HoverCard.Root>
				<HoverCard.Trigger>
					<Button variant="link">@acme-corp</Button>
				</HoverCard.Trigger>
				<HoverCard.Content class="w-64">
					<div class="flex gap-3">
						<Avatar.Root>
							<Avatar.Fallback>AC</Avatar.Fallback>
						</Avatar.Root>
						<div class="space-y-1">
							<p class="text-sm font-medium">Acme Corp</p>
							<p class="text-xs text-muted-foreground">Enterprise Plan · 12 instances</p>
							<Badge class="mt-1 border-emerald-500/20 bg-emerald-500/10 text-emerald-500"
								>Active</Badge
							>
						</div>
					</div>
				</HoverCard.Content>
			</HoverCard.Root>
		</div>
	</section>
</div>
