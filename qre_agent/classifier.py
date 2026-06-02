"""
Activity classifier for IRC §41 4-part test:
  1. Technological uncertainty
  2. Process of experimentation
  3. Technical nature (hard sciences, engineering, software)
  4. Qualified purpose (new/improved functionality — not style, taste, social science)
"""
from enum import Enum


class ActivityType(str, Enum):
    new_product = "new_product"
    improved_product = "improved_product"
    software_development = "software_development"
    process_improvement = "process_improvement"
    basic_research = "basic_research"
    non_qualified = "non_qualified"


# Keyword sets for heuristic classification
_KEYWORD_MAP: dict[ActivityType, list[str]] = {
    ActivityType.software_development: [
        "software", "algorithm", "api", "platform", "machine learning", "ml", "ai",
        "neural", "database", "architecture", "framework", "compiler", "encryption",
        "protocol", "distributed", "cloud", "microservice",
    ],
    ActivityType.basic_research: [
        "research", "study", "laboratory", "experiment", "hypothesis", "prototype",
        "clinical", "scientific", "discovery", "theory",
    ],
    ActivityType.new_product: [
        "new product", "novel", "invention", "patent", "launch", "develop",
        "build new", "create new", "design new",
    ],
    ActivityType.improved_product: [
        "improve", "enhance", "upgrade", "optimize", "refine", "augment",
        "performance", "efficiency", "reliability",
    ],
    ActivityType.process_improvement: [
        "process", "manufacturing", "production", "workflow", "automation",
        "pipeline", "yield", "throughput", "quality control",
    ],
    ActivityType.non_qualified: [
        "marketing", "advertising", "sales", "aesthetic", "style", "taste",
        "social science", "art", "humanities", "economics study",
        "management training", "routine testing",
    ],
}

# Qualified activity types (non_qualified excluded)
QUALIFIED_TYPES: frozenset[ActivityType] = frozenset(
    t for t in ActivityType if t != ActivityType.non_qualified
)


def classify_activity(description: str) -> ActivityType:
    """Classify an R&D activity description using keyword heuristics."""
    lower = description.lower()

    # Non-qualified check has highest priority — disqualifies immediately
    for kw in _KEYWORD_MAP[ActivityType.non_qualified]:
        if kw in lower:
            return ActivityType.non_qualified

    # Score each qualified category
    scores: dict[ActivityType, int] = {t: 0 for t in QUALIFIED_TYPES}
    for activity_type, keywords in _KEYWORD_MAP.items():
        if activity_type == ActivityType.non_qualified:
            continue
        for kw in keywords:
            if kw in lower:
                scores[activity_type] += 1

    best = max(scores, key=lambda t: scores[t])
    return best if scores[best] > 0 else ActivityType.basic_research


def is_qualified_activity(activity_type: ActivityType) -> bool:
    return activity_type in QUALIFIED_TYPES
