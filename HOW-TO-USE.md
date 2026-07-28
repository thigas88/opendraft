# OpenDraft: Comprehensive How-To Guide

Welcome to the new **OpenDraft** workflow! With the integration of the Open Paper Machine features, OpenDraft has evolved from a simple generator into a **complete 9-phase autonomous research engine**.

This guide explains how to use the entire pipeline end-to-end, taking advantage of the new Phase 0 gatekeeping, automatic figure generation, citation verification, and revision automation loops.

---

## The 9-Phase Pipeline

1.  **Phase 0 (Idea Evaluation):** Validates your research idea before investing time.
2.  **Phase 1 & 2 (Research):** Systematic literature search (CrossRef, Semantic Scholar, etc.).
3.  **Phase 3 (Structure):** Creates the research outline.
4.  **Phase 4 (Compose):** Drafts the text using targeted agents.
5.  **Phase 5 (Figures):** Automatically generates diagrams/plots via PaperBanana.
6.  **Phase 6 (Export):** Generates PDF, Word, and LaTeX.
7.  **Phase 7 (Verify):** Enhanced citation verification (Tier A).
8.  **Phase 8 (Revision):** PDF-driven automated revision loop.

---

## 1. Evaluating your Research Idea (Phase 0)

Before generating a 20,000-word draft, it's best to verify if the idea is scientifically viable. This phase applies the RS1–RS8 research strategy principles.

```bash
opendraft evaluate-idea "The impact of micro-dosing caffeine on endurance sports" --level research_paper
```

**What it does:**
- Runs the `idea-critic` and `research-strategist` agents.
- Tests the idea against 7 dimensions (novelty, feasibility, relevance, etc.).
- Outputs a **Verdict**: `PURSUE`, `REFINE`, `PARK`, or `KILL`.
- Saves a detailed evaluation report in the `research-evaluations/` directory.

---

## 2. Generating the Paper (Phases 1-6)

Once your idea is validated, you can start the main generation pipeline.

```bash
opendraft "The impact of micro-dosing caffeine on endurance sports" --level research_paper
```

**Pro-tip:** If you already ran `evaluate-idea` and received a `PURSUE` verdict, you can skip the gatekeeping phase during generation to save time and API tokens:

```bash
opendraft "Your Topic Here" --skip-evaluation
```

### What happens automatically:
- **Research & Structure:** Agents pull real papers and build an outline.
- **Compose:** Agents write the Introduction, Literature Review, Methodology, Results, Discussion, and Conclusion.
- **🎨 NEW: Figure Generation (Phase 5):** During the Compose phase, the AI will automatically identify where visual aids are needed. It will insert `[FIGURE: diagram]` or `[FIGURE: plot]` markers, and OpenDraft will invoke `paperbanana` to generate real PNG images, automatically injecting them into the LaTeX/Markdown output!
- **Export:** You will receive a ZIP file containing the `.md`, `.pdf`, `.docx`, and `.tex` formats.

---

## 3. Verifying Citations (Phase 7)

OpenDraft uses real citations, but LLMs can sometimes misuse a real paper to support an unrelated claim (hallucinated context). Phase 7 allows you to verify the exact claims against the actual source material.

```bash
opendraft verify-citations path/to/your_generated_draft.md
```

**What it does:**
- Extracts all claims paired with parenthetical citations `(Author, Year)`.
- Fetches the original abstract of the cited paper using the Crossref API (Tier A verification).
- Runs an AI judge to verify if the source abstract actually supports the claim.
- Outputs a **`verification_report.md`** with verdicts: `VERIFIED`, `MISMATCH`, `PLAUSIBLE`, or `UNVERIFIABLE`.

---

## 4. Automating Revisions with Reviewer Feedback (Phase 8)

The most powerful new feature is the Revision Loop. Instead of manually editing the generated text, you can act like a supervisor.

1. Take the generated PDF (`final_draft.pdf`).
2. Open it in any PDF reader (Adobe Acrobat, Preview, Edge).
3. Use the **Highlight** tool or add **Sticky Notes** to leave feedback (e.g., *"Expand on this methodology"*, *"This section is too brief"*).
4. Save the annotated PDF (e.g., `feedback_from_supervisor.pdf`).

Now, feed the annotated PDF back into OpenDraft:

```bash
opendraft revise path/to/output_folder/ path/to/feedback_from_supervisor.pdf
```

**What it does:**
- Uses `PyMuPDF` to extract your highlights and comments directly from the PDF.
- Maps your comments to the markdown source code.
- Instructs the `Crafter` agents to rewrite the sections exactly as requested.
- Outputs a new version (e.g., `final_draft_v2.md`, `.pdf`, `.docx`).

---

## 5. Other Helpful Commands

**Generate a 5-bullet TL;DR of any PDF (even non-OpenDraft papers):**
```bash
opendraft tldr path/to/any_paper.pdf
```

**Generate an Audio Podcast Digest of a paper (Requires ElevenLabs):**
```bash
opendraft digest path/to/any_paper.pdf --voice adam
```

**Fetch empirical datasets (World Bank, Eurostat, OWID):**
```bash
opendraft data search "GDP growth"
opendraft data worldbank NY.GDP.MKTP.CD --countries USA;DEU --start 2020
```

---

## Requirements for Advanced Features

To use all features, ensure your `.env` file is properly configured:

```env
GOOGLE_API_KEY=your_gemini_api_key      # Required for Core Generation, Idea Eval, Verification, Revisions
ELEVENLABS_API_KEY=your_key             # Optional: For Audio Digests
```

Make sure the optional dependencies are installed for PDF extraction and figure generation:
```bash
pip install paperbanana matplotlib seaborn pymupdf
```
