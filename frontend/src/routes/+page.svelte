<script lang="ts">
	import QueryBox from "$lib/components/QueryBox.svelte";
	import ResultsList from "$lib/components/ResultsList.svelte";
	import type { SearchResult } from "$lib/types/api.js";
	import { writable } from "svelte/store";

	const query = writable("");
	const results = writable<SearchResult[]>([]);
	const loading = writable(false);

	async function handleSearch(searchQuery: string) {
		query.set(searchQuery);
		loading.set(true);
		results.set([]);

		try {
			// Mock API call - replace with actual backend endpoint later
			// const response = await fetch('/api/search', {
			// 	method: 'POST',
			// 	headers: { 'Content-Type': 'application/json' },
			// 	body: JSON.stringify({ query: searchQuery })
			// });
			// const data: SearchResponse = await response.json();
			// results.set(data.results);

			// Mock response for now
			await new Promise((resolve) => setTimeout(resolve, 500));
			results.set([
				{
					id: "1",
					text: "This is a mock search result. Replace this with actual API integration.",
					source: { docId: "heroes", page: 42 },
				},
			]);
		} catch (error) {
			console.error("Search error:", error);
			results.set([]);
		} finally {
			loading.set(false);
		}
	}
</script>

<div class="search-page">
	<div class="search-container">
		<h1 class="title">Rules Lawyer</h1>
		<QueryBox
			bind:query={$query}
			loading={$loading}
			onSubmit={handleSearch}
		/>
		{#if $loading || $results.length > 0}
			<ResultsList results={$results} />
		{/if}
	</div>
</div>

<style>
	.search-page {
		min-height: 100vh;
		display: flex;
		align-items: flex-start;
		justify-content: center;
		padding: 2rem 1rem;
		background-color: #fff;
	}

	.search-container {
		width: 100%;
		max-width: 900px;
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.title {
		font-size: 3rem;
		font-weight: 300;
		color: #1a1a1a;
		margin-bottom: 2rem;
		letter-spacing: -0.5px;
	}

	@media (max-width: 768px) {
		.title {
			font-size: 2rem;
		}

		.search-page {
			padding: 1rem;
		}
	}
</style>
