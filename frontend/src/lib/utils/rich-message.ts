export function escapeHtml(value: string): string {
	return value
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&#039;');
}

export function formatInlineMarkdown(value: string): string {
	let html = escapeHtml(value);
	html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
	html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
	html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>');
	html = html.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');
	html = html.replace(/_([^_\n]+)_/g, '<em>$1</em>');
	html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+|mailto:[^\s)]+)\)/g, (_match, label, url) => {
		const safeUrl = escapeHtml(url);
		return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${label}</a>`;
	});
	return html;
}

export function renderFormattedMessage(content: string): string {
	const lines = content.replace(/\r\n/g, '\n').split('\n');
	const blocks: string[] = [];
	let paragraph: string[] = [];
	let listItems: string[] = [];

	function flushParagraph() {
		if (paragraph.length === 0) return;
		blocks.push(`<p>${paragraph.map(formatInlineMarkdown).join('<br>')}</p>`);
		paragraph = [];
	}

	function flushList() {
		if (listItems.length === 0) return;
		blocks.push(`<ul>${listItems.map((item) => `<li>${formatInlineMarkdown(item)}</li>`).join('')}</ul>`);
		listItems = [];
	}

	for (const rawLine of lines) {
		const line = rawLine.trimEnd();
		if (!line.trim()) {
			flushParagraph();
			flushList();
			continue;
		}

		const heading = line.match(/^(#{1,3})\s+(.+)$/);
		if (heading) {
			flushParagraph();
			flushList();
			const level = Math.min(heading[1].length + 2, 4);
			blocks.push(`<h${level}>${formatInlineMarkdown(heading[2])}</h${level}>`);
			continue;
		}

		const bullet = line.match(/^\s*[-*]\s+(.+)$/);
		const numbered = line.match(/^\s*\d+[.)]\s+(.+)$/);
		if (bullet || numbered) {
			flushParagraph();
			listItems.push((bullet ?? numbered)?.[1] ?? line);
			continue;
		}

		flushList();
		paragraph.push(line.trim());
	}

	flushParagraph();
	flushList();
	return blocks.join('');
}
