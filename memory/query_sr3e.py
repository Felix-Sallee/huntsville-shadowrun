#!/usr/bin/env python3
"""
SR3E Query Tool - Search Shadowrun 3rd Edition rules

Usage:
  python query_sr3e.py "damage"           # Single term search
  python query_sr3e.py "essence cost"    # Phrase search
  python query_sr3e.py --top 5 "magic rating"  # Limit results
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter

INDEX_PATH = "/Users/felixagent/.openclaw/workspace-herrick/memory/sr3e_index.json"
MEMORY_DIR = "/Users/felixagent/.openclaw/workspace-herrick/memory"


def load_index():
    with open(INDEX_PATH, "r") as f:
        return json.load(f)


def search(query, top=10):
    """Search index for query terms"""
    index = load_index()
    
    # Tokenize query
    query_terms = [t.lower().strip('.,!?;:"\'()[]{}-') 
                   for t in query.split() if len(t) > 2]
    
    results = []
    seen_lines = set()
    
    for term in query_terms:
        if term not in index["term_index"]:
            continue
        
        for match in index["term_index"][term]:
            # Avoid duplicate lines from different terms
            line_key = (match["file"], match["line"])
            if line_key not in seen_lines:
                seen_lines.add(line_key)
                results.append({
                    "term": term,
                    **match
                })
    
    # Sort by relevance (more matches = higher priority)
    term_counts = Counter(query_terms)
    results.sort(key=lambda x: -term_counts[x["term"]])
    
    return results[:top]


def get_context(file_name, start_line, end_line):
    """Get full context for a search result"""
    file_path = Path(MEMORY_DIR) / file_name
    lines = file_path.read_text().split('\n')
    
    # Adjust indices (1-based line numbers in index → 0-based in list)
    start_idx = max(0, start_line - 3)
    end_idx = min(len(lines), end_line + 2)
    
    context_lines = lines[start_idx:end_idx]
    return '\n'.join(context_lines)


def parse_args(args):
    """Parse command line arguments"""
    query_parts = []
    
    for arg in args:
        if arg.startswith('--'):
            parts = arg.split('=', 1)
            if len(parts) == 2:
                key, value = parts
            else:
                key, value = parts[0], '5'  # default top=5
            
            if key == 'top':
                return {'query': ' '.join(query_parts), 'top': int(value)}
        else:
            query_parts.append(arg)
    
    # No flags provided
    top = 5
    query = ' '.join(query_parts) if query_parts else ''
    return {'query': query, 'top': top}


def main():
    args = sys.argv[1:]  # Skip script name
    parsed = parse_args(args)
    query = parsed['query']
    top = parsed['top']
    
    if not query:
        print("Usage: python query_sr3e.py \"search query\"")
        print("Examples:")
        print('  python query_sr3e.py "damage"')
        print('  python query_sr3e.py "essence cost"')
        sys.exit(1)
    
    results = search(query, top=top)
    
    if not results:
        print(f"No matches found for: '{query}'")
        sys.exit(0)
    
    # Group by file
    by_file = defaultdict(list)
    for r in results:
        by_file[r["file"]].append(r)
    
    for file_name, matches in sorted(by_file.items()):
        print(f"\n=== {file_name} ===")
        
        # Get context once per file (using first match's line range)
        first_match = matches[0]
        context = get_context(file_name, 
                             first_match["context_start"], 
                             first_match["context_end"])
        print(context[:800])  # Limit output length
        
        print(f"\n--- Search terms found: {', '.join(r['term'] for r in matches)} ---")


if __name__ == "__main__":
    main()
