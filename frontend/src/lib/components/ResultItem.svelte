<script lang="ts">
	import type { SearchResult } from '$lib/types/api.js';
	import { goto } from '$app/navigation';

	export let result: SearchResult;

	function handleClick() {
		goto(`/viewer?doc=${result.source.docId}&page=${result.source.page}`);
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			handleClick();
		}
	}

	function getDocName(docId: string): string {
		return docId === 'heroes' ? 'Heroes' : 'Monsters';
	}
</script>

<div class="result-item" on:click={handleClick} on:keydown={handleKeydown} role="button" tabindex="0">
	<div class="result-text">{result.text}</div>
	<div class="result-source">
		{getDocName(result.source.docId)} • Page {result.source.page}
	</div>
</div>

<style>
	.result-item {
		padding: 1rem;
		border: 1px solid #dfe1e5;
		border-radius: 8px;
		cursor: pointer;
		transition: box-shadow 0.2s, border-color 0.2s;
		background-color: #fff;
	}

	.result-item:hover {
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		border-color: #4285f4;
	}

	.result-item:focus {
		outline: 2px solid #4285f4;
		outline-offset: 2px;
	}

	.result-text {
		color: #1a1a1a;
		line-height: 1.6;
		margin-bottom: 0.5rem;
		font-size: 0.95rem;
	}

	.result-source {
		color: #80868b;
		font-size: 0.85rem;
	}
</style>

