<script lang="ts">
	export let query: string = '';
	export let loading: boolean = false;
	export let onSubmit: (query: string) => void = () => {};

	let inputElement: HTMLInputElement;

	function handleSubmit() {
		if (query.trim() && !loading) {
			onSubmit(query.trim());
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			handleSubmit();
		}
	}
</script>

<div class="query-box">
	<input
		bind:this={inputElement}
		bind:value={query}
		on:keydown={handleKeydown}
		placeholder="Search rules..."
		disabled={loading}
		class="search-input"
	/>
	<button
		type="button"
		on:click={handleSubmit}
		disabled={loading || !query.trim()}
		class="search-button"
	>
		{loading ? 'Searching...' : 'Search'}
	</button>
</div>

<style>
	.query-box {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
		width: 100%;
		max-width: 600px;
		margin: 0 auto;
	}

	.search-input {
		width: 100%;
		padding: 0.75rem 1rem;
		font-size: 1rem;
		border: 1px solid #dfe1e5;
		border-radius: 24px;
		outline: none;
		transition: box-shadow 0.2s;
	}

	.search-input:focus {
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		border-color: #4285f4;
	}

	.search-input:disabled {
		background-color: #f5f5f5;
		cursor: not-allowed;
	}

	.search-button {
		padding: 0.5rem 1.5rem;
		font-size: 0.9rem;
		color: #fff;
		background-color: #4285f4;
		border: none;
		border-radius: 4px;
		cursor: pointer;
		transition: background-color 0.2s;
	}

	.search-button:hover:not(:disabled) {
		background-color: #357ae8;
	}

	.search-button:disabled {
		background-color: #c6c6c6;
		cursor: not-allowed;
	}
</style>

