<script lang="ts">
	import * as pdfjsLib from 'pdfjs-dist';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	let container: HTMLDivElement;
	let canvas: HTMLCanvasElement;
	let pdfDoc: pdfjsLib.PDFDocumentProxy | null = null;
	let currentPage = 1;
	let totalPages = 0;
	let loading = true;
	let error: string | null = null;
	let currentDocId: string = '';
	let currentPageNum: number = 0;

	// Set worker
	pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;

	$: docId = $page.url.searchParams.get('doc') || 'heroes';
	$: pageNum = parseInt($page.url.searchParams.get('page') || '1', 10);

	onMount(async () => {
		currentDocId = docId;
		currentPageNum = pageNum;
		await loadPDF();
	});

	// Watch for URL changes and reload PDF if doc or page changed
	$: {
		if (docId !== currentDocId || pageNum !== currentPageNum) {
			currentDocId = docId;
			currentPageNum = pageNum;
			loadPDF();
		}
	}

	async function loadPDF() {
		loading = true;
		error = null;

		try {
			const pdfPath = `/pdfs/${docId}.pdf`;
			const loadingTask = pdfjsLib.getDocument(pdfPath);
			pdfDoc = await loadingTask.promise;
			totalPages = pdfDoc.numPages;

			// Navigate to the specified page
			if (pageNum > 0 && pageNum <= totalPages) {
				currentPage = pageNum;
				await renderPage(pageNum);
			} else {
				await renderPage(1);
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load PDF';
			console.error('Error loading PDF:', err);
		} finally {
			loading = false;
		}
	}

	async function renderPage(pageNum: number) {
		if (!pdfDoc || !canvas) return;

		const page = await pdfDoc.getPage(pageNum);
		const viewport = page.getViewport({ scale: 1.5 });

		canvas.height = viewport.height;
		canvas.width = viewport.width;

		const context = canvas.getContext('2d');
		if (!context) return;

		const renderContext = {
			canvasContext: context,
			viewport: viewport
		};

		await page.render(renderContext).promise;
		currentPage = pageNum;
	}

	async function goToPage(pageNum: number) {
		if (pageNum < 1 || pageNum > totalPages) return;
		await renderPage(pageNum);
		// Update URL without navigation
		const url = new URL(window.location.href);
		url.searchParams.set('page', pageNum.toString());
		window.history.replaceState({}, '', url);
	}

	async function previousPage() {
		if (currentPage > 1) {
			await goToPage(currentPage - 1);
		}
	}

	async function nextPage() {
		if (currentPage < totalPages) {
			await goToPage(currentPage + 1);
		}
	}

	function goBack() {
		goto('/');
	}
</script>

<div class="viewer-container">
	<div class="viewer-header">
		<button class="back-button" on:click={goBack}>← Back to Search</button>
		<div class="page-info">
			<span>{currentPage} / {totalPages}</span>
			<span class="doc-name">{docId === 'heroes' ? 'Heroes' : 'Monsters'}</span>
		</div>
	</div>

	<div class="viewer-content">
		{#if loading}
			<div class="loading">Loading PDF...</div>
		{:else if error}
			<div class="error">{error}</div>
		{:else}
			<div class="canvas-container" bind:this={container}>
				<canvas bind:this={canvas}></canvas>
			</div>
			<div class="controls">
				<button
					class="nav-button"
					on:click={previousPage}
					disabled={currentPage <= 1}
				>
					Previous
				</button>
				<input
					type="number"
					class="page-input"
					bind:value={currentPage}
					min="1"
					max={totalPages}
					on:change={(e) => goToPage(parseInt(e.target.value, 10))}
				/>
				<span class="total-pages">/ {totalPages}</span>
				<button
					class="nav-button"
					on:click={nextPage}
					disabled={currentPage >= totalPages}
				>
					Next
				</button>
			</div>
		{/if}
	</div>
</div>

<style>
	.viewer-container {
		display: flex;
		flex-direction: column;
		height: 100vh;
		background-color: #525252;
	}

	.viewer-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem;
		background-color: #fff;
		border-bottom: 1px solid #dfe1e5;
	}

	.back-button {
		padding: 0.5rem 1rem;
		background-color: #f5f5f5;
		border: 1px solid #dfe1e5;
		border-radius: 4px;
		cursor: pointer;
		font-size: 0.9rem;
		transition: background-color 0.2s;
	}

	.back-button:hover {
		background-color: #e8e8e8;
	}

	.page-info {
		display: flex;
		gap: 1rem;
		align-items: center;
		font-size: 0.9rem;
		color: #5f6368;
	}

	.doc-name {
		font-weight: 500;
		color: #1a1a1a;
	}

	.viewer-content {
		flex: 1;
		overflow: auto;
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 2rem;
	}

	.canvas-container {
		margin-bottom: 1rem;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
	}

	canvas {
		display: block;
		background-color: #fff;
	}

	.controls {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		background-color: #fff;
		padding: 0.75rem 1rem;
		border-radius: 8px;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}

	.nav-button {
		padding: 0.5rem 1rem;
		background-color: #4285f4;
		color: #fff;
		border: none;
		border-radius: 4px;
		cursor: pointer;
		font-size: 0.9rem;
		transition: background-color 0.2s;
	}

	.nav-button:hover:not(:disabled) {
		background-color: #357ae8;
	}

	.nav-button:disabled {
		background-color: #c6c6c6;
		cursor: not-allowed;
	}

	.page-input {
		width: 60px;
		padding: 0.5rem;
		border: 1px solid #dfe1e5;
		border-radius: 4px;
		text-align: center;
		font-size: 0.9rem;
	}

	.total-pages {
		color: #5f6368;
		font-size: 0.9rem;
	}

	.loading,
	.error {
		padding: 2rem;
		text-align: center;
		color: #fff;
		font-size: 1rem;
	}

	.error {
		color: #f44336;
	}
</style>

