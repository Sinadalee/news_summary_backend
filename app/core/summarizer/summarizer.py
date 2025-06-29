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
    def __init__(self, region, date_str=None, base_dir="data", top_k=5, frequency_minutes=60, use_llm=True):
        load_dotenv()
        self.region = region
        self.top_k = top_k
        self.use_llm = use_llm
        self.frequency_minutes = frequency_minutes
        self.llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0) if use_llm else None

        self.date = date_str or datetime.utcnow().strftime("%Y-%m-%d")
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw" / self.region / self.date
        self.cache_dir = self.base_dir / "score_cache" / self.region / self.date
        self.summary_dir = self.base_dir / "summaries"
        self.log_dir = self.base_dir / "log" / "process_log"
        self.status_file = self.base_dir / "cache" / "article_status.json"
        self.archive_dir = self.base_dir / "archive" / "raw" / self.region / self.date

        for path in [self.cache_dir, self.log_dir, self.status_file.parent, self.archive_dir]:
            path.mkdir(parents=True, exist_ok=True)

        self.llm_prompt = PromptTemplate.from_template("""
Summarize the following news article in 2-3 sentences and rate its importance (1-10) for the source region and globally:

Source Region: {region}

Title: {title}
Summary: {summary}

Return as JSON:
{{
  "summary": "...",
  "impact": {{"{region}": int, "global": int}}
}}
""")

        self.llm_chain = LLMChain(llm=self.llm, prompt=self.llm_prompt) if use_llm else None

        # Load status DB
        if self.status_file.exists():
            with open(self.status_file, "r") as f:
                self.article_status = json.load(f)
        else:
            self.article_status = {}

    def load_new_articles(self):
        articles = []
        fetch_files_used = set()

        if not self.raw_dir.exists():
            self.raw_dir.mkdir(parents=True, exist_ok=True)
            return [], set()

        for source_dir in self.raw_dir.iterdir():
            if not source_dir.is_dir():
                continue

            for fpath in sorted(source_dir.glob("fetched_*.json")):
                fetch_name = fpath.stem.replace("fetched_", "")

                try:
                    with open(fpath, "r") as f:
                        items = json.load(f)
                        valid_items = []
                        for item in items:
                            item["fetch_name"] = fetch_name
                            link = item.get("link")
                            if link not in self.article_status or self.article_status[link]["status"] != "done":
                                valid_items.append(item)
                        if valid_items:
                            articles.extend(valid_items)
                            fetch_files_used.add(str(fpath))
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
                if fuzz.token_set_ratio(a["title"], articles[j]["title"]) > 85 or \
                   fuzz.token_set_ratio(a["summary"], articles[j]["summary"]) > 85:
                    group.append(articles[j])
                    used.add(j)
            groups.append(group)
        return groups

    def summarize_and_score(self, title, summary):
        if not self.use_llm:
            return summary, {self.region: 0, "global": 0}
        try:
            result = self.llm_chain.run({"title": title, "summary": summary, "region": self.region})
            parsed = json.loads(result)
            return parsed["summary"], parsed["impact"]
        except Exception:
            return summary, {self.region: 0, "global": 0}

    def update(self):
        articles, fetch_files_used = self.load_new_articles()
        if not articles:
            print(f"[{self.region.upper()}] No new articles to process.")
            return

        grouped = self.group_articles(articles)
        cache_results = {}
        processed_files = set()

        for group in grouped:
            best = group[0]
            uuid = generate_article_id(best['title'], best['link'])

            # Skip if already marked as done
            if best['link'] in self.article_status and self.article_status[best['link']]['status'] == 'done':
                continue

            cache_path = self.cache_dir / f"{uuid}.json"
            if cache_path.exists():
                with open(cache_path) as f:
                    cache_results[uuid] = json.load(f)
            else:
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
                with open(cache_path, "w") as f:
                    json.dump(cache_results[uuid], f, indent=2)

            # Mark article as processed
            self.article_status[best['link']] = {"uuid": uuid, "status": "done"}

        now = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")

        # Save updated status DB
        with open(self.status_file, "w") as f:
            json.dump(self.article_status, f, indent=2)

        # Move processed fetched_*.json files
        for fpath in fetch_files_used:
            try:
                f = Path(fpath)
                archive_path = self.archive_dir / f.parent.name
                archive_path.mkdir(parents=True, exist_ok=True)
                f.rename(archive_path / f.name)
            except Exception as e:
                print(f"[ERROR] Failed to move {fpath}: {e}")

        # Write process log
        log_path = self.log_dir / f"summarizer_{self.region}_{now}.json"
        with open(log_path, "w") as f:
            json.dump({
                "run_time": now,
                "region": self.region,
                "fetch_files": list(fetch_files_used),
                "uuids_processed": list(cache_results.keys())
            }, f, indent=2)

        print(f"[{self.region.upper()}] Processed {len(articles)} articles into {len(grouped)} groups.")