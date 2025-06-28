import os
import json
import hashlib
from collections import defaultdict
from dotenv import load_dotenv
from fuzzywuzzy import fuzz
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from datetime import datetime
from pathlib import Path


def generate_article_id(title: str, link: str) -> str:
    unique_str = f"{title}-{link}"
    return hashlib.sha256(unique_str.encode()).hexdigest()


class Summarizer:
    def __init__(self, date_str=None, base_dir="data", top_k=5, write_per_source=False, frequency_minutes=60, use_llm=True):
        load_dotenv()
        self.top_k = top_k
        self.use_llm = use_llm
        self.frequency_minutes = frequency_minutes
        self.llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0) if use_llm else None

        self.date = date_str or datetime.utcnow().strftime("%Y-%m-%d")
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw" / self.date
        self.score_dir = self.base_dir / "score" / self.date
        self.cache_dir = self.base_dir / "score_cache" / self.date
        self.summary_dir = self.base_dir / "summaries"
        self.log_dir = self.base_dir / "log" / "process_log"

        for path in [self.score_dir, self.cache_dir, self.summary_dir, self.log_dir]:
            path.mkdir(parents=True, exist_ok=True)

        self.regions = json.load(open("app/config/regions.json"))

        self.llm_prompt = PromptTemplate.from_template("""
Summarize the following news article in 2-3 sentences and rate its importance (1-10) for each of the following regions:

Regions: {regions}

Title: {title}
Summary: {summary}

Return as JSON:
{{
  "summary": "...",
  "impact": {{"region1": int, "region2": int, ...}}
}}
""")

        self.llm_chain = LLMChain(llm=self.llm, prompt=self.llm_prompt) if use_llm else None

    def list_processed_fetch_files(self):
        processed = set()
        for file in self.log_dir.glob("*.json"):
            try:
                with open(file) as f:
                    log = json.load(f)
                    processed.update(log.get("fetch_files", []))
            except Exception:
                continue
        return processed

    def load_new_articles(self):
        articles = []
        processed = self.list_processed_fetch_files()
        fetch_files_used = set()

        for source_dir in self.raw_dir.iterdir():
            if not source_dir.is_dir():
                continue

            for fpath in sorted(source_dir.glob("fetched_*.json")):
                fetch_name = fpath.stem.replace("fetched_", "")
                if fetch_name in processed:
                    print(f"[SKIP] Already processed: {fpath}")
                    continue

                try:
                    with open(fpath, "r") as f:
                        items = json.load(f)
                        for item in items:
                            item["fetch_name"] = fetch_name
                            articles.append(item)
                        fetch_files_used.add(fetch_name)
                except Exception as e:
                    print(f"[ERROR] Failed to read {fpath}: {e}")

        return articles, fetch_files_used

    def group_articles(self, articles):
        groups = []
        used = set()
        for i, a in enumerate(articles):
            if i in used:
                continue
            group = [a]
            for j in range(i + 1, len(articles)):
                if j in used:
                    continue
                if fuzz.token_set_ratio(a["title"], articles[j]["title"]) > 85 or fuzz.token_set_ratio(a["summary"], articles[j]["summary"]) > 85:
                    group.append(articles[j])
                    used.add(j)
            groups.append(group)
        return groups

    def summarize_and_score(self, title, summary):
        if not self.use_llm:
            return summary, {region: 0 for region in self.regions}
        try:
            result = self.llm_chain.run({"title": title, "summary": summary, "regions": ", ".join(self.regions)})
            parsed = json.loads(result)
            return parsed["summary"], parsed["impact"]
        except Exception:
            return summary, {region: 0 for region in self.regions}

    def update(self):
        articles, fetch_files_used = self.load_new_articles()
        if not articles:
            print("No new articles to process.")
            return

        grouped = self.group_articles(articles)
        cache_results = {}

        for group in grouped:
            best = group[0]
            uuid = generate_article_id(best['title'], best['link'])
            if (self.cache_dir / f"{uuid}.json").exists():
                with open(self.cache_dir / f"{uuid}.json") as f:
                    cache_results[uuid] = json.load(f)
                continue
            summary, impact = self.summarize_and_score(best["title"], best["summary"])
            cache_results[uuid] = {
                "uuid": uuid,
                "title": best["title"],
                "summary": summary,
                "link": best["link"],
                "source_url": best["source_url"],
                "published": min(a["published"] for a in group),
                "frequency": len(group),
                "impact": impact,
            }
            with open(self.cache_dir / f"{uuid}.json", "w") as f:
                json.dump(cache_results[uuid], f, indent=2)

        now = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")

        # Process log
        log_path = self.log_dir / f"summarizer_{now}.json"
        with open(log_path, "w") as f:
            json.dump({
                "run_time": now,
                "fetch_files": list(fetch_files_used),
                "uuids_processed": list(cache_results.keys()),
                "regions": list(self.regions)
            }, f, indent=2)

        print(f"Processed {len(articles)} articles into {len(grouped)} groups.")