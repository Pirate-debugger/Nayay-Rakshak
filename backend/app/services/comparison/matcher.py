import re
from typing import List, Optional, Set, Tuple

from app.schemas.comparison import StructuralDiff
from app.services.comparison.segmenter import ComparisonClause


def normalize_ocr_text(text: str) -> str:
    """
    Normalizes common OCR artifacts and typographic substitutions in legal documents:
    - Smart quotes, em-dashes, en-dashes, typographic ellipses
    - Ligatures (fi, fl, etc.)
    - Digit substitutions (e.g., 'l' or 'I' instead of 1 in numeric contexts, 'O' instead of 0 in numbers)
    - Collapse excessive spaces
    """
    if not text:
        return ""

    s = text
    # Smart quotes & dashes
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    s = s.replace("—", "-").replace("–", "-").replace("…", "...")
    s = s.replace("ﬁ", "fi").replace("ﬂ", "fl")

    # Fix OCR digit substitutions: 'l' or 'I' for 1
    s = re.sub(r"(?<=[₹$Rs\.\s])([lI])(?=[0-9])", "1", s)
    s = re.sub(r"\b([lI])(?=[0-9])", "1", s)
    s = re.sub(r"(?<=[0-9])([lI])", "1", s)

    # Fix OCR digit substitutions: 'O' or 'o' for 0 in numbers (e.g. 15,OOO or 3O,OOO or l0th)
    for _ in range(4):
        s = re.sub(r"(?<=[0-9,₹$])([Oo])(?=[0-9,Oo]|\b)", "0", s)
        s = re.sub(r"\b([Oo])(?=[0-9,])", "0", s)

    # Whitespace cleanup
    s = re.sub(r"\s+", " ", s).strip()
    return s


def compute_token_jaccard(set_a: Set[str], set_b: Set[str]) -> float:
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return intersection / union if union > 0 else 0.0


def compute_char_dice(text_a: str, text_b: str) -> float:
    """Character bi-gram dice coefficient for robust typo/OCR noise comparison."""
    if text_a == text_b:
        return 1.0
    if len(text_a) < 2 or len(text_b) < 2:
        return 1.0 if text_a.strip().lower() == text_b.strip().lower() else 0.0

    a_lower = text_a.lower()
    b_lower = text_b.lower()

    ngrams_a = [a_lower[i : i + 2] for i in range(len(a_lower) - 1)]
    ngrams_b = [b_lower[i : i + 2] for i in range(len(b_lower) - 1)]

    set_a = set(ngrams_a)
    set_b = set(ngrams_b)

    common = sum(min(ngrams_a.count(ng), ngrams_b.count(ng)) for ng in (set_a & set_b))
    total = len(ngrams_a) + len(ngrams_b)
    return (2.0 * common) / total if total > 0 else 0.0


def compute_heading_overlap(h_a: str, h_b: str) -> float:
    stop_words = {"clause", "section", "article", "and", "the", "of", "to", "for", "in"}
    toks_a = {
        w.lower() for w in re.findall(r"\w+", h_a) if w.lower() not in stop_words and len(w) > 2
    }
    toks_b = {
        w.lower() for w in re.findall(r"\w+", h_b) if w.lower() not in stop_words and len(w) > 2
    }

    if not toks_a or not toks_b:
        return 0.0
    return compute_token_jaccard(toks_a, toks_b)


def compute_clause_similarity(clause_a: ComparisonClause, clause_b: ComparisonClause) -> float:
    """
    Computes weighted semantic & lexical similarity score between two clauses.
    Combines:
    1. Normalized character dice (0.35)
    2. Token Jaccard (0.45)
    3. Heading alignment (0.20)
    """
    norm_a = normalize_ocr_text(clause_a.text)
    norm_b = normalize_ocr_text(clause_b.text)

    # Exact normalized match
    if norm_a.lower() == norm_b.lower():
        return 1.0

    char_sim = compute_char_dice(norm_a, norm_b)

    # Meaningful legal tokens (exclude basic grammar stop words)
    stop_words = {
        "the",
        "and",
        "or",
        "of",
        "to",
        "a",
        "an",
        "is",
        "in",
        "it",
        "that",
        "this",
        "by",
        "for",
        "with",
        "as",
    }
    t_a = {t for t in clause_a.tokens if t not in stop_words}
    t_b = {t for t in clause_b.tokens if t not in stop_words}
    token_sim = compute_token_jaccard(t_a, t_b)

    heading_sim = compute_heading_overlap(clause_a.section_heading, clause_b.section_heading)

    # If headings strongly match (e.g. "TERMINATION" vs "TERMINATION"), give strong anchor
    total_score = (0.35 * char_sim) + (0.45 * token_sim) + (0.20 * heading_sim)
    return round(min(1.0, max(0.0, total_score)), 4)


class AlignedClausePair:
    def __init__(
        self,
        clause_a: Optional[ComparisonClause],
        clause_b: Optional[ComparisonClause],
        similarity: float,
        is_reordered: bool = False,
    ):
        self.clause_a = clause_a
        self.clause_b = clause_b
        self.similarity = similarity
        self.is_reordered = is_reordered


def match_document_clauses(
    clauses_a: List[ComparisonClause],
    clauses_b: List[ComparisonClause],
    min_match_threshold: float = 0.28,
) -> Tuple[List[AlignedClausePair], StructuralDiff]:
    """
    Bipartite alignment of clauses between Document A and Document B.
    Handles:
    - Reordered clauses across sections
    - Missing clauses in B (present in A)
    - Newly added clauses in B (absent in A)
    - Structural alignment calculation
    """
    # 1. Compute pairwise similarity matrix
    scores: List[Tuple[float, int, int]] = []
    for i, ca in enumerate(clauses_a):
        for j, cb in enumerate(clauses_b):
            sim = compute_clause_similarity(ca, cb)
            if sim >= min_match_threshold:
                scores.append((sim, i, j))

    # Sort candidates descending by similarity
    scores.sort(key=lambda x: x[0], reverse=True)

    matched_a: Set[int] = set()
    matched_b: Set[int] = set()
    matches: List[Tuple[int, int, float]] = []

    for sim, i, j in scores:
        if i not in matched_a and j not in matched_b:
            matched_a.add(i)
            matched_b.add(j)
            matches.append((i, j, sim))

    # Sort matches by index in A to determine ordering alignment
    matches.sort(key=lambda x: x[0])

    # Check for reordering: compare the order of j indices against monotonic increase
    aligned_pairs: List[AlignedClausePair] = []
    last_j = -1
    reordered_count = 0

    for i, j, sim in matches:
        is_reordered = False
        if j < last_j:
            is_reordered = True
            reordered_count += 1
        last_j = max(last_j, j)
        aligned_pairs.append(
            AlignedClausePair(
                clause_a=clauses_a[i],
                clause_b=clauses_b[j],
                similarity=sim,
                is_reordered=is_reordered,
            )
        )

    # Unmatched in A -> Missing in B
    missing_in_b_count = 0
    for i, ca in enumerate(clauses_a):
        if i not in matched_a:
            aligned_pairs.append(
                AlignedClausePair(clause_a=ca, clause_b=None, similarity=0.0, is_reordered=False)
            )
            missing_in_b_count += 1

    # Unmatched in B -> New in B
    new_in_b_count = 0
    for j, cb in enumerate(clauses_b):
        if j not in matched_b:
            aligned_pairs.append(
                AlignedClausePair(clause_a=None, clause_b=cb, similarity=0.0, is_reordered=False)
            )
            new_in_b_count += 1

    # Compute structural alignment score
    total_unique = max(1, len(clauses_a) + len(clauses_b) - len(matches))
    raw_alignment = len(matches) / total_unique
    reorder_penalty = (reordered_count * 0.05) if len(matches) > 0 else 0.0
    alignment_score = max(0.0, min(1.0, raw_alignment - reorder_penalty))

    structural_diff = StructuralDiff(
        doc_a_clause_count=len(clauses_a),
        doc_b_clause_count=len(clauses_b),
        aligned_clause_count=len(matches),
        reordered_clause_count=reordered_count,
        missing_in_b_count=missing_in_b_count,
        new_in_b_count=new_in_b_count,
        structural_alignment_score=round(alignment_score, 3),
    )

    return aligned_pairs, structural_diff
