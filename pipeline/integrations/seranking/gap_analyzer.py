#!/usr/bin/env python3
"""
AEO Content Gap Analyzer
Finds long-tail, question-based content gaps optimized for Answer Engine Optimization (AEO)
Targets: ChatGPT, Google AI Overviews, Perplexity, Bing Copilot

Author: GrowthGPT
Version: 1.0.0
"""

import requests
import json
import csv
import os
from typing import List, Dict, Optional
from datetime import datetime
import argparse
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.environ.get("SERANKING_API_KEY")
if not API_KEY:
    raise ValueError("SERANKING_API_KEY environment variable is required. Please set it in your .env file.")

BASE_URL = "https://api.seranking.com/v1"
HEADERS = {
    "Authorization": f"Token {API_KEY}",
    "Content-Type": "application/json"
}

# AEO-Optimized Filtering Criteria
AEO_FILTERS = {
    "min_volume": 100,
    "max_volume": 5000,
    "max_difficulty": 35,
    "max_competition": 0.3,
    "min_words": 3,
}

# AEO Intent Keywords
AEO_INTENT_PATTERNS = {
    "question": {
        "keywords": ["how", "what", "why", "when", "where", "who", "can", "should", "does", "is", "are", "will", "would"],
        "multiplier": 1.5,  # Highest priority for AEO
        "description": "Question-based queries - Perfect for featured snippets & AI answers"
    },
    "commercial": {
        "keywords": ["best", "top", "vs", "versus", "review", "compare", "pricing", "cost", "alternative"],
        "multiplier": 1.3,
        "description": "Commercial intent - Good for AI recommendations"
    },
    "informational": {
        "keywords": ["guide", "tutorial", "tips", "examples", "template", "checklist", "definition", "meaning"],
        "multiplier": 1.4,  # High for AEO
        "description": "Informational queries - Excellent for AI citations"
    },
    "list": {
        "keywords": ["list", "ways to", "steps to", "types of", "kinds of", "ideas for"],
        "multiplier": 1.4,
        "description": "List-based queries - Perfect for structured answers"
    },
    "local": {
        "keywords": ["near me", "in", "local", "nearby", "around"],
        "multiplier": 1.1,
        "description": "Local queries"
    },
}

# SERP Features that indicate AEO opportunity
AEO_SERP_FEATURES = [
    "people_also_ask",
    "featured_snippet",
    "sge",  # Search Generative Experience / AI Overviews
    "knowledge_panel",
    "faq"
]


class SEORankingAPI:
    """SE Ranking API client"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json"
        }
        self.base_url = BASE_URL

    def get_competitors(self, domain: str, source: str = "us", limit: int = 5) -> List[Dict]:
        """Get top competitors for a domain"""
        url = f"{self.base_url}/domain/competitors"
        params = {
            "source": source,
            "domain": domain,
            "limit": limit
        }

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching competitors: {e}")
            return []

    def get_keyword_comparison(self, domain: str, compare_domain: str,
                               source: str = "us", limit: int = 1000) -> List[Dict]:
        """Get keywords that competitor ranks for but target domain doesn't"""
        url = f"{self.base_url}/domain/keywords/comparison"
        params = {
            "source": source,
            "domain": domain,
            "compare": compare_domain,
            "type": "organic",
            "diff": 1,  # Keywords competitor has that you don't
            "limit": limit,
            "order_field": "difficulty",
            "order_type": "asc"
        }

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching keyword comparison: {e}")
            return []


class AEOContentGapAnalyzer:
    """Analyzes content gaps with AEO optimization"""

    def __init__(self, api: SEORankingAPI):
        self.api = api

    def filter_longtail_aeo(self, keywords: List[Dict],
                            filters: Optional[Dict] = None) -> List[Dict]:
        """Filter keywords for long-tail AEO opportunities"""
        if filters is None:
            filters = AEO_FILTERS

        longtail = []

        for kw in keywords:
            volume = kw.get("volume", 0)
            difficulty = kw.get("difficulty", 100)
            competition = kw.get("competition", 1)
            keyword_text = kw.get("keyword", "")
            word_count = len(keyword_text.split())

            # Apply AEO-optimized filters
            if (filters["min_volume"] <= volume <= filters["max_volume"] and
                difficulty <= filters["max_difficulty"] and
                competition <= filters["max_competition"] and
                word_count >= filters["min_words"]):

                # Add metadata
                kw["word_count"] = word_count
                longtail.append(kw)

        return longtail

    def categorize_by_intent(self, keyword: Dict) -> Dict:
        """Categorize keyword by AEO intent and add multiplier"""
        keyword_lower = keyword["keyword"].lower()
        matched_intents = []
        max_multiplier = 1.0
        primary_intent = "other"

        for intent, config in AEO_INTENT_PATTERNS.items():
            if any(pattern in keyword_lower for pattern in config["keywords"]):
                matched_intents.append(intent)
                if config["multiplier"] > max_multiplier:
                    max_multiplier = config["multiplier"]
                    primary_intent = intent

        keyword["intent"] = primary_intent
        keyword["intent_multiplier"] = max_multiplier
        keyword["matched_intents"] = matched_intents

        return keyword

    def check_aeo_serp_features(self, keyword: Dict) -> Dict:
        """Check if keyword has AEO-friendly SERP features"""
        serp_features = keyword.get("serp_features", [])

        aeo_features = [f for f in serp_features if f in AEO_SERP_FEATURES]
        keyword["aeo_serp_features"] = aeo_features
        keyword["has_aeo_features"] = len(aeo_features) > 0

        # Boost score if has AEO features
        if keyword["has_aeo_features"]:
            keyword["aeo_feature_boost"] = 1.3
        else:
            keyword["aeo_feature_boost"] = 1.0

        return keyword

    def calculate_aeo_score(self, keyword: Dict) -> float:
        """
        Calculate AEO opportunity score

        AEO Score = (Volume × Intent Multiplier × SERP Feature Boost) / (Difficulty + 1)

        Higher score = better AEO opportunity
        """
        volume = keyword.get("volume", 0)
        difficulty = keyword.get("difficulty", 100)
        intent_multiplier = keyword.get("intent_multiplier", 1.0)
        aeo_feature_boost = keyword.get("aeo_feature_boost", 1.0)

        # AEO-optimized scoring
        aeo_score = (volume * intent_multiplier * aeo_feature_boost) / (difficulty + 1)

        keyword["aeo_score"] = round(aeo_score, 2)
        return aeo_score

    def analyze_content_gaps(self, domain: str, competitors: Optional[List[str]] = None,
                            source: str = "us", max_competitors: int = 3) -> List[Dict]:
        """
        Analyze content gaps for AEO optimization

        Args:
            domain: Target domain to analyze
            competitors: List of competitor domains (optional, will auto-detect if not provided)
            source: Region code (default: "us")
            max_competitors: Maximum number of competitors to analyze

        Returns:
            List of AEO-optimized keyword opportunities
        """
        print(f"\n🔍 Analyzing AEO Content Gaps for: {domain}")
        print("=" * 60)

        # Get competitors if not provided
        if not competitors:
            print(f"\n📊 Finding top {max_competitors} competitors...")
            competitor_data = self.api.get_competitors(domain, source, max_competitors)
            competitors = [c["domain"] for c in competitor_data[:max_competitors]]
            print(f"Found competitors: {', '.join(competitors)}")

        all_gaps = []

        # Analyze each competitor
        for i, competitor in enumerate(competitors, 1):
            print(f"\n[{i}/{len(competitors)}] Comparing with {competitor}...")

            # Get keyword gaps
            gaps = self.api.get_keyword_comparison(domain, competitor, source)

            if gaps:
                print(f"  → Found {len(gaps)} total keyword gaps")

                # Filter for long-tail AEO opportunities
                longtail = self.filter_longtail_aeo(gaps)
                print(f"  → Filtered to {len(longtail)} long-tail AEO opportunities")

                # Categorize and score
                for kw in longtail:
                    kw["competitor"] = competitor
                    self.categorize_by_intent(kw)
                    self.check_aeo_serp_features(kw)
                    self.calculate_aeo_score(kw)

                all_gaps.extend(longtail)

        # Sort by AEO score (highest first)
        all_gaps.sort(key=lambda x: x["aeo_score"], reverse=True)

        print(f"\n✅ Total AEO opportunities found: {len(all_gaps)}")

        return all_gaps

    def generate_summary_stats(self, gaps: List[Dict]) -> Dict:
        """Generate summary statistics"""
        if not gaps:
            return {}

        # Intent breakdown
        intent_counts = {}
        for gap in gaps:
            intent = gap.get("intent", "other")
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

        # AEO feature breakdown
        with_aeo_features = sum(1 for g in gaps if g.get("has_aeo_features", False))

        # Question keywords (highest priority for AEO)
        question_kw = [g for g in gaps if g.get("intent") == "question"]

        return {
            "total_opportunities": len(gaps),
            "intent_breakdown": intent_counts,
            "with_aeo_serp_features": with_aeo_features,
            "question_keywords": len(question_kw),
            "avg_aeo_score": round(sum(g["aeo_score"] for g in gaps) / len(gaps), 2),
            "avg_volume": round(sum(g["volume"] for g in gaps) / len(gaps)),
            "avg_difficulty": round(sum(g["difficulty"] for g in gaps) / len(gaps), 1),
        }

    def export_to_csv(self, gaps: List[Dict], filename: str):
        """Export results to CSV"""
        if not gaps:
            print("No gaps to export")
            return

        fieldnames = [
            "keyword", "volume", "difficulty", "cpc", "competition",
            "aeo_score", "intent", "word_count", "has_aeo_features",
            "aeo_serp_features", "competitor", "url", "position"
        ]

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(gaps)

        print(f"\n💾 Exported {len(gaps)} opportunities to: {filename}")

    def export_to_json(self, gaps: List[Dict], filename: str):
        """Export results to JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(gaps, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Exported {len(gaps)} opportunities to: {filename}")

    def print_top_opportunities(self, gaps: List[Dict], top_n: int = 20):
        """Print top AEO opportunities"""
        if not gaps:
            print("\n❌ No opportunities found")
            return

        print(f"\n🎯 TOP {min(top_n, len(gaps))} AEO OPPORTUNITIES")
        print("=" * 100)

        for i, kw in enumerate(gaps[:top_n], 1):
            print(f"\n{i}. {kw['keyword']}")
            print(f"   Volume: {kw['volume']:,}/mo | Difficulty: {kw['difficulty']} | AEO Score: {kw['aeo_score']}")
            print(f"   Intent: {kw['intent'].upper()} | Words: {kw['word_count']} | Competitor: {kw['competitor']}")

            if kw.get('has_aeo_features'):
                print(f"   🎁 SERP Features: {', '.join(kw['aeo_serp_features'])}")

            if kw.get('cpc', 0) > 0:
                print(f"   CPC: ${kw['cpc']:.2f} | Competition: {kw['competition']:.2f}")


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="AEO Content Gap Analyzer - Find long-tail opportunities for Answer Engine Optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze domain with auto-detected competitors
  python aeo_content_gap_analyzer.py --domain hubspot.com

  # Analyze specific competitors
  python aeo_content_gap_analyzer.py --domain hubspot.com --competitors salesforce.com zoho.com

  # Export to CSV
  python aeo_content_gap_analyzer.py --domain hubspot.com --export csv --output gaps.csv

  # Customize filters
  python aeo_content_gap_analyzer.py --domain hubspot.com --min-volume 200 --max-difficulty 25

  # Show top 50 opportunities
  python aeo_content_gap_analyzer.py --domain hubspot.com --top 50
        """
    )

    parser.add_argument("--domain", required=True, help="Target domain to analyze")
    parser.add_argument("--competitors", nargs="+", help="List of competitor domains")
    parser.add_argument("--source", default="us", help="Region code (default: us)")
    parser.add_argument("--max-competitors", type=int, default=3, help="Max competitors to auto-detect (default: 3)")
    parser.add_argument("--min-volume", type=int, default=100, help="Minimum search volume (default: 100)")
    parser.add_argument("--max-volume", type=int, default=5000, help="Maximum search volume (default: 5000)")
    parser.add_argument("--max-difficulty", type=int, default=35, help="Maximum difficulty (default: 35)")
    parser.add_argument("--max-competition", type=float, default=0.3, help="Maximum competition (default: 0.3)")
    parser.add_argument("--min-words", type=int, default=3, help="Minimum word count (default: 3)")
    parser.add_argument("--export", choices=["csv", "json", "both"], help="Export format")
    parser.add_argument("--output", default="aeo_content_gaps", help="Output filename (without extension)")
    parser.add_argument("--top", type=int, default=20, help="Number of top opportunities to display (default: 20)")

    args = parser.parse_args()

    # Custom filters
    custom_filters = {
        "min_volume": args.min_volume,
        "max_volume": args.max_volume,
        "max_difficulty": args.max_difficulty,
        "max_competition": args.max_competition,
        "min_words": args.min_words,
    }

    # Initialize API and analyzer
    api_key = os.environ.get("SERANKING_API_KEY")
    if not api_key:
        print("❌ Error: SERANKING_API_KEY environment variable is required")
        print("   Please set it in your .env file: SERANKING_API_KEY=your_api_key_here")
        sys.exit(1)
    
    api = SEORankingAPI(api_key)
    analyzer = AEOContentGapAnalyzer(api)

    # Temporarily store custom filters
    original_method = analyzer.filter_longtail_aeo

    def filter_with_custom(kw_list, filters=None):
        return original_method(kw_list, custom_filters)

    analyzer.filter_longtail_aeo = filter_with_custom

    # Analyze content gaps
    gaps = analyzer.analyze_content_gaps(
        domain=args.domain,
        competitors=args.competitors,
        source=args.source,
        max_competitors=args.max_competitors
    )

    if gaps:
        # Print summary stats
        stats = analyzer.generate_summary_stats(gaps)
        print(f"\n📊 SUMMARY STATISTICS")
        print("=" * 60)
        print(f"Total Opportunities: {stats['total_opportunities']}")
        print(f"Question Keywords (High Priority): {stats['question_keywords']}")
        print(f"With AEO SERP Features: {stats['with_aeo_serp_features']}")
        print(f"\nIntent Breakdown:")
        for intent, count in sorted(stats['intent_breakdown'].items(), key=lambda x: x[1], reverse=True):
            description = AEO_INTENT_PATTERNS.get(intent, {}).get('description', 'Other')
            print(f"  • {intent.capitalize()}: {count} - {description}")
        print(f"\nAverage Metrics:")
        print(f"  • AEO Score: {stats['avg_aeo_score']}")
        print(f"  • Volume: {stats['avg_volume']}/mo")
        print(f"  • Difficulty: {stats['avg_difficulty']}")

        # Print top opportunities
        analyzer.print_top_opportunities(gaps, args.top)

        # Export if requested
        if args.export:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if args.export in ["csv", "both"]:
                csv_filename = f"{args.output}_{timestamp}.csv"
                analyzer.export_to_csv(gaps, csv_filename)

            if args.export in ["json", "both"]:
                json_filename = f"{args.output}_{timestamp}.json"
                analyzer.export_to_json(gaps, json_filename)


if __name__ == "__main__":
    main()
