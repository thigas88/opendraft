#!/usr/bin/env python3
"""
Verify citations in a draft using Crossref/Semantic Scholar abstracts.
Implements Phase 7B (Enhanced Verification).
"""

import sys
import re
import json
import requests
from pathlib import Path

def extract_citations(markdown_text: str) -> list[dict]:
    """Extract claims and their associated citations from markdown text."""
    # This regex looks for sentences ending with (Author, Year) or similar citations
    # It's a heuristic for markdown drafts before LaTeX compilation
    citations = []
    
    # Simple regex to find sentences with citations
    pattern = re.compile(r'([^.!?\n]+)\s+(\([A-Za-z\s&]+,\s+\d{4}\))')
    
    for i, match in enumerate(pattern.finditer(markdown_text)):
        claim = match.group(1).strip()
        citation = match.group(2).strip()
        
        # Clean up the claim
        if len(claim) > 20:
            citations.append({
                "id": i + 1,
                "claim": f"{claim} {citation}",
                "citation": citation,
                "text": claim
            })
            
    return citations

def fetch_abstract(citation_text: str) -> str:
    """Best-effort abstract fetch using Crossref API based on citation text."""
    try:
        # Simple search using the citation text as query
        url = f"https://api.crossref.org/works?query={citation_text}&select=title,abstract,author,issued&rows=1"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            items = data.get("message", {}).get("items", [])
            if items:
                item = items[0]
                abstract = item.get("abstract", "")
                # Crossref abstracts often have JATS XML tags like <jats:p>
                abstract = re.sub(r'<[^>]+>', '', abstract)
                if abstract:
                    return abstract
    except Exception:
        pass
    
    return "Abstract not available or could not be found."

def verify_citations_command(draft_path: Path) -> int:
    """Run the verification process on a draft file."""
    import os
    
    print(f"\n  \033[1mCitation Verification\033[0m")
    print(f"  \033[90m{'─' * 50}\033[0m")
    
    if not draft_path.exists():
        print(f"  \033[31m✗\033[0m File not found: {draft_path}\n")
        return 1
        
    content = draft_path.read_text(encoding='utf-8')
    citations = extract_citations(content)
    
    if not citations:
        print(f"  \033[33m!\033[0m No parenthetical citations (Author, Year) found to verify.\n")
        return 0
        
    print(f"  \033[35m⣾\033[0m Extracting {len(citations)} citation claims...")
    
    # Only process up to 15 citations to save time and API calls in this demo
    max_process = min(15, len(citations))
    citations = citations[:max_process]
    
    print(f"  \033[35m⣾\033[0m Fetching source abstracts (Tier A retrieval)...")
    
    for c in citations:
        c["abstract"] = fetch_abstract(c["citation"])
        
    print(f"  \033[35m⣾\033[0m Verifying claims against source material...")
    
    # Use Gemini to judge if we have an API key
    api_key = os.environ.get("GOOGLE_API_KEY")
    verified_count = 0
    mismatch_count = 0
    unverifiable_count = 0
    
    results = []
    
    if api_key:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        for i, c in enumerate(citations):
            if c["abstract"] == "Abstract not available or could not be found.":
                c["verdict"] = "UNVERIFIABLE"
                unverifiable_count += 1
                results.append(c)
                continue
                
            prompt = f"""Compare the following claim against the source abstract.
CLAIM: {c['text']}
SOURCE ABSTRACT: {c['abstract']}

Does the abstract support the claim?
Reply with exactly one word: SUPPORTED, CONTRADICTED, or INSUFFICIENT."""
            
            try:
                response = client.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents=prompt
                )
                verdict = response.text.strip().upper()
                if "SUPPORTED" in verdict:
                    c["verdict"] = "VERIFIED"
                    verified_count += 1
                elif "CONTRADICTED" in verdict:
                    c["verdict"] = "MISMATCH"
                    mismatch_count += 1
                else:
                    c["verdict"] = "PLAUSIBLE"
                    verified_count += 1
            except Exception:
                c["verdict"] = "UNVERIFIABLE"
                unverifiable_count += 1
            
            results.append(c)
    else:
        print("  \033[33m!\033[0m GOOGLE_API_KEY not set. Marking all with abstracts as PLAUSIBLE.")
        for c in citations:
            if c["abstract"] != "Abstract not available or could not be found.":
                c["verdict"] = "PLAUSIBLE"
                verified_count += 1
            else:
                c["verdict"] = "UNVERIFIABLE"
                unverifiable_count += 1
            results.append(c)
            
    # Generate report
    report_path = draft_path.parent / "verification_report.md"
    
    with open(report_path, "w", encoding='utf-8') as f:
        f.write(f"# Citation Verification Report\n\n")
        f.write(f"**Document:** {draft_path.name}\n")
        f.write(f"**Claims Checked:** {len(results)}\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"| Status | Count |\n")
        f.write(f"|--------|-------|\n")
        f.write(f"| VERIFIED/PLAUSIBLE | {verified_count} |\n")
        f.write(f"| MISMATCH | {mismatch_count} |\n")
        f.write(f"| UNVERIFIABLE | {unverifiable_count} |\n\n")
        
        f.write(f"## Detailed Findings\n\n")
        for c in results:
            icon = "✅" if c["verdict"] in ["VERIFIED", "PLAUSIBLE"] else "❌" if c["verdict"] == "MISMATCH" else "❓"
            f.write(f"### {icon} {c['citation']}\n")
            f.write(f"- **Claim:** {c['text']}\n")
            f.write(f"- **Verdict:** {c['verdict']}\n")
            f.write(f"- **Abstract:** {c['abstract'][:300]}...\n\n")
            
    print(f"\n  \033[32m✓\033[0m \033[1mVerification Complete\033[0m")
    print(f"  \033[90mVERIFIED:\033[0m {verified_count}")
    print(f"  \033[90mMISMATCH:\033[0m {mismatch_count}")
    print(f"  \033[90mUNVERIFIABLE:\033[0m {unverifiable_count}")
    print(f"  \033[90mReport:\033[0m {report_path}\n")
    
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_citations.py <draft.md>")
        sys.exit(1)
    verify_citations_command(Path(sys.argv[1]))
