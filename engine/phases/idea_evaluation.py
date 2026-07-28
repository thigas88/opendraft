#!/usr/bin/env python3
"""
ABOUTME: Phase 0 — Idea Evaluation Gate (ported from Open Paper Machine)
ABOUTME: Evaluates research ideas using RS1-RS8 principles before committing to production

This phase implements the "evaluate before producing" philosophy from the Open Paper Machine.
It uses structured evaluation across 7 dimensions, the Conclusion-First Test (RS2),
and the Nugget Test (RS3) to determine if a research idea is worth pursuing.

Verdicts:
  PURSUE — Proceed to Phase 1 (Research)
  REFINE — Suggest modifications, then re-evaluate or proceed
  PARK   — Not now, but potentially later
  KILL   — Not worth pursuing; extract salvageable value
"""

import re
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from .context import DraftContext

logger = logging.getLogger(__name__)

# Default dimensions for structured evaluation
EVALUATION_DIMENSIONS = [
    "Novelty",       # RS1: How many months until someone else does this?
    "Impact",        # RS2: Does the conclusion write itself compellingly?
    "Timing",        # RS8: Is the field ready for this contribution?
    "Feasibility",   # Can this be executed with available resources?
    "Competition",   # RS7: How crowded is the research space?
    "Nugget",        # RS3: Can the key insight be stated in one sentence?
    "Narrative",     # Does the paper tell a compelling story?
]

VERDICT_OPTIONS = ["PURSUE", "REFINE", "PARK", "KILL"]

# Prompt for idea evaluation agent
IDEA_EVALUATION_PROMPT = """You are an expert research advisor performing a structured evaluation
of a research idea. You combine Nicholas Carlini's research philosophy with systematic
evaluation to determine whether this paper is worth writing.

## Research Strategy Principles (RS1-RS8)

### Problem Selection
- **RS1 (Novelty Test):** If you don't do this, how many months until someone else does?
- **RS2 (Conclusion-First Test):** Can you write a compelling conclusion right now?
- **RS3 (Nugget Test):** Can you state the key insight in one sentence?

### Execution Strategy
- **RS4 (Fail Fast):** Start with the sub-problem most likely to kill the project.
- **RS5 (Kill Early):** A working project with low impact is worse than a killed project.
- **RS6 (Unreasonable Effort):** Strengthen "sometimes" to "usually" — but only AFTER RS4 and RS5.

### Strategic Positioning
- **RS7 (Comparative Advantage):** Research space is high-dimensional; find your unique corner.
- **RS8 (Timing Awareness):** Impact = skill × domain importance at this moment.

## Evaluation Task

Evaluate the following research idea across 7 dimensions. For each dimension, provide:
1. A rating (use the scale specified below)
2. A brief justification (2-3 sentences)

### Rating Scales:
- **Novelty:** Years | Months | Weeks (time until someone else does it)
- **Impact:** High | Medium | Low
- **Timing:** Well-Timed | Acceptable | Too Early | Too Late
- **Feasibility:** Low Risk | Medium Risk | High Risk
- **Competition:** Open | Moderate | Crowded
- **Nugget:** Clear | Fuzzy | Missing
- **Narrative:** Compelling | Workable | Weak

### Then provide:
1. **The Nugget** — One sentence capturing the core insight
2. **Draft Conclusion** — 2-3 sentences: What can we say? What changed? So what?
3. **Draft Abstract** — 5 sentences following Carlini's Formula A:
   (1) Topic, (2) Problem, (3) Results/Methods, (4) The other, (5) Why it matters
4. **Key Risks** — Top 3 risks that could kill this project
5. **Recommended First Step** — The single action most likely to de-risk the project (RS4)
6. **Final Verdict** — PURSUE, REFINE, PARK, or KILL with reasoning

### Critical Rule:
If the Draft Conclusion feels hollow or generic — if it only says "our method achieves X%
improvement" — that IS the signal. The idea doesn't have enough impact to justify the work.
Kill it honestly.

## Output Format

Respond in JSON format:
```json
{
  "dimensions": {
    "Novelty": {"rating": "...", "justification": "..."},
    "Impact": {"rating": "...", "justification": "..."},
    "Timing": {"rating": "...", "justification": "..."},
    "Feasibility": {"rating": "...", "justification": "..."},
    "Competition": {"rating": "...", "justification": "..."},
    "Nugget": {"rating": "...", "justification": "..."},
    "Narrative": {"rating": "...", "justification": "..."}
  },
  "nugget": "One sentence core insight",
  "draft_conclusion": "2-3 sentences...",
  "draft_abstract": "5 sentences following Formula A...",
  "key_risks": ["Risk 1", "Risk 2", "Risk 3"],
  "recommended_first_step": "The single action to de-risk...",
  "verdict": "PURSUE|REFINE|PARK|KILL",
  "verdict_reasoning": "Why this verdict...",
  "refinement_suggestions": ["Only if REFINE verdict"],
  "salvageable_ideas": ["Only if KILL verdict"],
  "park_revisit_conditions": ["Only if PARK verdict"]
}
```
"""


def run_idea_evaluation(ctx: DraftContext) -> None:
    """
    Execute Phase 0: Idea Evaluation Gate.

    Evaluates the research topic using RS1-RS8 principles and structured
    7-dimension assessment. Sets ctx.idea_evaluation with results and
    ctx.idea_verdict with the final decision.

    Mutates ctx: idea_evaluation, idea_verdict, idea_nugget, idea_draft_abstract,
                 idea_draft_conclusion, idea_key_risks
    """
    from utils.agent_runner import run_agent, rate_limit_delay
    from utils.text_utils import smart_truncate

    if ctx.verbose:
        print("\n🧠 PHASE 0: IDEA EVALUATION")
        print("   Evaluating whether this research idea is worth pursuing...")

    if ctx.tracker:
        ctx.tracker.log_activity(
            "🧠 Phase 0: Evaluating research idea",
            event_type="info",
            phase="idea_evaluation"
        )

    # Check for prior evaluations
    evaluations_dir = ctx.folders['root'] / "research-evaluations"
    evaluations_dir.mkdir(parents=True, exist_ok=True)
    prior = _check_prior_evaluations(evaluations_dir, ctx.topic)
    if prior:
        logger.info(f"Found prior evaluation: {prior['verdict']} from {prior['date']}")
        if ctx.verbose:
            print(f"   ℹ️  Prior evaluation found: {prior['verdict']} from {prior['date']}")

    # Build evaluation input
    eval_input = f"Research Topic: {ctx.topic}"
    if ctx.blurb:
        eval_input += f"\nResearch Focus/Context: {ctx.blurb}"
    eval_input += f"\nAcademic Level: {ctx.academic_level}"
    eval_input += f"\nLanguage: {ctx.language_name}"
    if prior:
        eval_input += f"\n\nPrior Evaluation ({prior['date']}): Verdict was {prior['verdict']}."
        eval_input += f"\nPrior reasoning: {prior.get('verdict_reasoning', 'N/A')}"
        eval_input += "\nRe-evaluate considering whether conditions have changed."

    # Run the evaluation agent
    eval_output = run_agent(
        model=ctx.model,
        name="Idea Evaluator - Phase 0 Gate",
        prompt_path="prompts/00_idea_evaluation/evaluator.md",
        user_input=eval_input,
        save_to=ctx.folders['root'] / "research-evaluations" / "latest_evaluation.md",
        skip_validation=ctx.skip_validation,
        verbose=ctx.verbose,
        token_tracker=ctx.token_tracker,
        token_stage="idea_evaluation",
    )

    # Parse the evaluation output
    evaluation = _parse_evaluation_output(eval_output)

    # Store results on context
    ctx.idea_evaluation = evaluation
    ctx.idea_verdict = evaluation.get("verdict", "PURSUE")
    ctx.idea_nugget = evaluation.get("nugget", "")
    ctx.idea_draft_abstract = evaluation.get("draft_abstract", "")
    ctx.idea_draft_conclusion = evaluation.get("draft_conclusion", "")
    ctx.idea_key_risks = evaluation.get("key_risks", [])

    # Save evaluation to file
    _save_evaluation(evaluations_dir, ctx.topic, evaluation)

    # Report results
    verdict = ctx.idea_verdict
    if ctx.verbose:
        _print_evaluation_summary(evaluation)

    if ctx.tracker:
        ctx.tracker.log_activity(
            f"{'✅' if verdict == 'PURSUE' else '⚠️' if verdict == 'REFINE' else '🛑'} "
            f"Idea evaluation: {verdict}",
            event_type="milestone",
            phase="idea_evaluation"
        )

    rate_limit_delay()


def _check_prior_evaluations(evaluations_dir: Path, topic: str) -> Optional[Dict[str, Any]]:
    """Check for prior evaluations of this topic."""
    for eval_file in sorted(evaluations_dir.glob("*.md"), reverse=True):
        try:
            content = eval_file.read_text(encoding='utf-8')
            # Simple check: does the file contain the topic?
            if topic.lower()[:30] in content.lower():
                # Try to extract verdict and date from YAML frontmatter
                yaml_match = re.search(
                    r'---\n(.*?)\n---', content, re.DOTALL
                )
                if yaml_match:
                    yaml_content = yaml_match.group(1)
                    verdict_match = re.search(r'verdict:\s*(\w+)', yaml_content)
                    date_match = re.search(r'date:\s*([\d-]+)', yaml_content)
                    reasoning_match = re.search(r'verdict_reasoning:\s*(.+)', yaml_content)
                    if verdict_match:
                        return {
                            "verdict": verdict_match.group(1),
                            "date": date_match.group(1) if date_match else "unknown",
                            "verdict_reasoning": reasoning_match.group(1) if reasoning_match else "",
                        }
        except Exception:
            continue
    return None


def _parse_evaluation_output(output: str) -> Dict[str, Any]:
    """Parse the evaluation agent's output, handling both JSON and markdown formats."""
    # Try to extract JSON from the output
    json_match = re.search(r'```json\s*\n(.*?)\n```', output, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from evaluation output")

    # Try plain JSON
    try:
        return json.loads(output)
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: extract key information from markdown
    evaluation = {
        "dimensions": {},
        "verdict": "PURSUE",  # Default to PURSUE if parsing fails
        "nugget": "",
        "draft_conclusion": "",
        "draft_abstract": "",
        "key_risks": [],
        "recommended_first_step": "",
        "verdict_reasoning": "Evaluation output could not be fully parsed; defaulting to PURSUE.",
    }

    # Try to extract verdict
    for verdict in VERDICT_OPTIONS:
        if verdict in output.upper():
            evaluation["verdict"] = verdict
            break

    # Try to extract nugget
    nugget_match = re.search(r'(?:nugget|key insight)[:\s]*(.+?)(?:\n|$)', output, re.IGNORECASE)
    if nugget_match:
        evaluation["nugget"] = nugget_match.group(1).strip()

    # Try to extract conclusion
    conclusion_match = re.search(
        r'(?:draft conclusion|conclusion)[:\s]*(.+?)(?:\n\n|\n#|$)',
        output, re.IGNORECASE | re.DOTALL
    )
    if conclusion_match:
        evaluation["draft_conclusion"] = conclusion_match.group(1).strip()

    # Try to extract dimensions
    for dim in EVALUATION_DIMENSIONS:
        dim_match = re.search(
            rf'{dim}[:\s]*(\w[\w\s]*?)(?:\n|—|-)',
            output, re.IGNORECASE
        )
        if dim_match:
            evaluation["dimensions"][dim] = {
                "rating": dim_match.group(1).strip(),
                "justification": ""
            }

    return evaluation


def _save_evaluation(evaluations_dir: Path, topic: str, evaluation: Dict[str, Any]) -> None:
    """Save evaluation results as a markdown file with YAML frontmatter."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = re.sub(r'[^\w\s-]', '', topic.lower())[:40]
    slug = re.sub(r'[\s_]+', '-', slug).strip('-')
    filename = f"{date_str}-{slug}.md"

    verdict = evaluation.get("verdict", "UNKNOWN")
    nugget = evaluation.get("nugget", "")

    content = f"""---
date: {date_str}
topic: "{topic[:100]}"
verdict: {verdict}
nugget: "{nugget[:200]}"
---

# Idea Evaluation: {topic[:100]}

## Verdict: {verdict}

{evaluation.get('verdict_reasoning', '')}

## Dimension Scores

| Dimension | Rating | Justification |
|-----------|--------|---------------|
"""
    for dim_name, dim_data in evaluation.get("dimensions", {}).items():
        if isinstance(dim_data, dict):
            rating = dim_data.get("rating", "N/A")
            justification = dim_data.get("justification", "")
        else:
            rating = str(dim_data)
            justification = ""
        content += f"| {dim_name} | {rating} | {justification} |\n"

    content += f"""
## The Nugget

{nugget}

## Draft Abstract

{evaluation.get('draft_abstract', 'N/A')}

## Draft Conclusion

{evaluation.get('draft_conclusion', 'N/A')}

## Key Risks

"""
    for i, risk in enumerate(evaluation.get("key_risks", []), 1):
        content += f"{i}. {risk}\n"

    content += f"""
## Recommended First Step

{evaluation.get('recommended_first_step', 'N/A')}
"""

    if verdict == "REFINE":
        content += "\n## Refinement Suggestions\n\n"
        for s in evaluation.get("refinement_suggestions", []):
            content += f"- {s}\n"

    if verdict == "KILL":
        content += "\n## Salvageable Ideas\n\n"
        for s in evaluation.get("salvageable_ideas", []):
            content += f"- {s}\n"

    if verdict == "PARK":
        content += "\n## Revisit Conditions\n\n"
        for s in evaluation.get("park_revisit_conditions", []):
            content += f"- {s}\n"

    filepath = evaluations_dir / filename
    filepath.write_text(content, encoding='utf-8')
    logger.info(f"Evaluation saved to {filepath}")


def _print_evaluation_summary(evaluation: Dict[str, Any]) -> None:
    """Print a formatted summary of the evaluation results."""
    verdict = evaluation.get("verdict", "UNKNOWN")
    verdict_icon = {
        "PURSUE": "✅", "REFINE": "🔄", "PARK": "⏸️", "KILL": "🛑"
    }.get(verdict, "❓")

    print(f"\n{'='*60}")
    print(f"   {verdict_icon} IDEA EVALUATION RESULT: {verdict}")
    print(f"{'='*60}")

    # Dimensions table
    dims = evaluation.get("dimensions", {})
    if dims:
        print(f"\n   {'Dimension':<14} {'Rating':<14}")
        print(f"   {'─'*14} {'─'*14}")
        for dim_name, dim_data in dims.items():
            rating = dim_data.get("rating", "N/A") if isinstance(dim_data, dict) else str(dim_data)
            print(f"   {dim_name:<14} {rating:<14}")

    # Nugget
    nugget = evaluation.get("nugget", "")
    if nugget:
        print(f"\n   💡 Nugget: {nugget[:80]}{'...' if len(nugget) > 80 else ''}")

    # Verdict reasoning
    reasoning = evaluation.get("verdict_reasoning", "")
    if reasoning:
        print(f"\n   📋 Reasoning: {reasoning[:120]}{'...' if len(reasoning) > 120 else ''}")

    # Key risks
    risks = evaluation.get("key_risks", [])
    if risks:
        print(f"\n   ⚠️  Key Risks:")
        for risk in risks[:3]:
            print(f"      • {risk[:80]}")

    print(f"{'='*60}\n")
