<script lang="ts">
	import type { SearchResult } from '$lib/types/api.js';
	import ResultItem from './ResultItem.svelte';

	export let results: SearchResult[] = [];
</script>

<div class="results-list">
	{#if results.length === 0}
		<div class="empty-state">No results found</div>
	{:else}
		{#each results as result (result.id)}
			<ResultItem {result} />
		{/each}
	{/if}
</div>

<style>
	.results-list {
		width: 100%;
		max-width: 800px;
		margin: 2rem auto 0;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.empty-state {
		text-align: center;
		color: #80868b;
		padding: 2rem;
		font-size: 0.9rem;
	}
</style>

