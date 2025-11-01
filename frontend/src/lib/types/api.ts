export interface SearchResult {
	id: string;
	text: string;
	source: {
		docId: string; // 'heroes' | 'monsters'
		page: number;
	};
}

export interface SearchResponse {
	results: SearchResult[];
}

