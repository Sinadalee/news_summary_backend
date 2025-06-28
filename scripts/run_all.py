import click
from app.core.fetcher import fetch_articles
from app.core.summarizer import Summarizer
from app.core.topk_precomputer import TopKPrecomputer


@click.command()
@click.option('--max-age', default=30, help='Max age (in days) of UUID cache to keep.')
@click.option('--use-llm', is_flag=True, help='Enable LLM for summarization and scoring.')
@click.option('--top-k', default=5, help='Number of top articles to compute per region.')
@click.option('--region-config', default='app/config/regions.json', help='Path to region config JSON.')
def run_all(max_age, use_llm, top_k, region_config):
    print(">>> Running fetcher...")
    articles = fetch_articles(max_age_days=max_age)
    print(f"Total new articles fetched: {len(articles)}")

    print(">>> Running summarizer...")
    summarizer = Summarizer(use_llm=use_llm)
    summarizer.update()

    print(">>> Running top_k precomputer...")
    precomputer = TopKPrecomputer(top_k=top_k, region_config=region_config)
    precomputer.precompute_top_k()


if __name__ == "__main__":
    run_all()