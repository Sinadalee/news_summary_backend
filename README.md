Title: Design Memo - Improved RSS Fetching Architecture

Objective:
Implement a reliable, traceable, and rerunnable system for fetching RSS news articles from multiple sources, suitable for incremental summarization and robust fault recovery.

⸻

Current Approach (Before Refactor):
	•	Fetch articles from all RSS sources.
	•	Use a single last_fetch.json file to store the latest timestamp for each source.
	•	Store all fetched data in one merged file: data/raw/fetched_TIMESTAMP.json.

Problems with Current Design:
	1.	Fragile State Management:
	•	If the fetch fails midway (e.g., one RSS source errors out), the last_fetch.json still gets updated for successful sources.
	•	This leads to missed articles and inconsistency.
	2.	Hard to Rerun:
	•	No way to easily identify what was fetched from which source and when.
	•	Rerunning requires manually adjusting timestamps in last_fetch.json.
	3.	Low Traceability:
	•	Merged dump makes it difficult to isolate issues with individual sources.

⸻

Improved Design (After Refactor):

Key Changes:
	1.	Per-Source Dumping:
	•	Each source has its own folder, e.g., data/raw/npr/, data/raw/cbsnews/.
	•	Each fetch is saved as fetched_YYYYMMDDTHHMMSS.json within its source folder.
	2.	Timestamp Tracking via Filenames:
	•	Instead of last_fetch.json, we infer the last fetch time from the latest filename in each folder.
	3.	Modular Fetching:
	•	Each source is fetched and processed independently.
	•	Easy to parallelize or retry individually.

Advantages:
	•	Rerunnable: Just delete or rename the problematic dump file and re-run.
	•	Traceable: Clear record of what was fetched and when, per source.
	•	Fault-tolerant: One bad source won’t block updates from others.
	•	Better debugging: Easy to isolate and inspect source-specific data.

Disadvantages:
	•	Slightly more storage used due to separated files.
	•	Slightly more I/O overhead when merging for summarization.

⸻

Why This Was Chosen:
This design prioritizes robustness and maintainability. In a real-world production system (or even a well-maintained prototype), deterministic fetch history and easy reprocessing are crucial. The improved design solves these real pains while keeping logic simple and extendable.