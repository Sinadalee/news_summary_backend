import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

class TopKPrecomputer:
    def __init__(self, base_dir="data", top_k=5, region_config="app/config/regions.json"):
        self.base_dir = Path(base_dir)
        self.score_dir = self.base_dir / "score_cache"
        self.output_dir = self.base_dir / "top_k_cache"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.top_k = top_k

        with open(region_config, "r") as f:
            self.regions = json.load(f)

    def load_scores(self, region) -> list:
        all_scores = []
        region_dir = self.score_dir / region
        if not region_dir.exists():
            return []

        for date_dir in region_dir.iterdir():
            if not date_dir.is_dir():
                continue
            for file in date_dir.glob("*.json"):
                try:
                    with open(file, "r") as f:
                        data = json.load(f)
                        if isinstance(data, dict) and "published" in data:
                            all_scores.append(data)
                except Exception as e:
                    print(f"[WARN] Failed to load {file}: {e}")
        return all_scores

    def already_computed_dates(self, region):
        region_dir = self.output_dir / region
        if not region_dir.exists():
            return set()
        return {f.stem for f in region_dir.glob("*.json") if f.is_file()}

    def precompute_top_k(self, regions=None, top_k=None, rerun_days=2):
        regions = regions or self.regions.keys()
        top_k = top_k or self.top_k
        today = datetime.now(timezone.utc).date()

        for region in regions:
            tzname = self.regions[region]
            tz = ZoneInfo(tzname)
            computed_dates = self.already_computed_dates(region)
            articles_by_date = {}

            all_scores = self.load_scores(region)
            for article in all_scores:
                try:
                    pub = article.get("published", "")
                    pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                    pub_local = pub_dt.astimezone(tz)
                    date_str = pub_local.strftime("%Y-%m-%d")
                    articles_by_date.setdefault(date_str, []).append(article)
                except Exception as e:
                    print(f"[WARN] Skipped bad article: {e}")

            for date_str, articles in articles_by_date.items():
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                should_force_rerun = (today - date_obj).days <= rerun_days

                if date_str in computed_dates and not should_force_rerun:
                    print(f"[SKIP] Already computed for {region} {date_str}")
                    continue

                top_k_items = self._compute_top_k(articles, region, top_k)
                out_path = self.output_dir / region / f"{date_str}.json"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with open(out_path, "w") as f:
                    json.dump(top_k_items, f, indent=2)
                print(f"[DONE] {region} {date_str} saved to {out_path}")

    def _compute_top_k(self, articles, region, top_k):
        scored = []
        for a in articles:
            try:
                impact = a.get("impact", {}).get(region, 0)
                freq = a.get("frequency", 1)
                a["_score"] = impact + freq
                scored.append(a)
            except Exception as e:
                print(f"[ERROR] Scoring article: {e}")

        scored.sort(key=lambda x: x["_score"], reverse=True)
        for a in scored:
            a.pop("_score", None)
        return scored[:top_k]