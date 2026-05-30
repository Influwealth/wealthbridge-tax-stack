"""
Documentation validator for IRC §41 audit readiness.

Checks required fields, description completeness, and returns a 0-100 score.
A score >= 70 is considered valid for filing purposes.
"""
from dataclasses import dataclass, field


PASSING_SCORE = 70  # minimum score to be audit-ready


@dataclass
class ValidationResult:
    is_valid: bool
    score: int
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


def validate_project_documentation(project_data: dict) -> ValidationResult:
    """
    Score a project dict for documentation completeness.
    Expected keys: project_name, description, activity_type, start_date,
                   end_date, principal_researcher, has_expenses.
    """
    score = 0
    issues: list[str] = []
    recommendations: list[str] = []

    # Required: project_name (10 pts)
    name = project_data.get("project_name", "")
    if name and len(name.strip()) >= 3:
        score += 10
    else:
        issues.append("Project name is missing or too short.")

    # Required: description (25 pts, scaled by length)
    description = project_data.get("description", "")
    desc_len = len(description.strip())
    if desc_len >= 200:
        score += 25
    elif desc_len >= 100:
        score += 15
        recommendations.append("Expand description to >= 200 characters for full credit.")
    elif desc_len >= 50:
        score += 8
        issues.append("Description is too brief. Provide detailed technical narrative.")
    else:
        issues.append("Description is missing or insufficient (< 50 characters).")

    # Required: activity_type classified (15 pts)
    activity_type = project_data.get("activity_type", "")
    if activity_type and activity_type != "non_qualified":
        score += 15
    elif activity_type == "non_qualified":
        issues.append("Activity classified as non-qualified. Review 4-part test.")
    else:
        issues.append("Activity type not classified.")

    # Optional: start_date (10 pts)
    if project_data.get("start_date"):
        score += 10
    else:
        recommendations.append("Add project start date for timeline documentation.")

    # Optional: end_date or ongoing flag (10 pts)
    if project_data.get("end_date") or project_data.get("is_ongoing"):
        score += 10
    else:
        recommendations.append("Add project end date or mark as ongoing.")

    # Optional: principal researcher named (10 pts)
    if project_data.get("principal_researcher"):
        score += 10
    else:
        recommendations.append("Name the principal researcher or technical lead.")

    # Optional: expenses documented (20 pts)
    if project_data.get("has_expenses") or project_data.get("expense_count", 0) > 0:
        score += 20
    else:
        issues.append("No expenses documented. QRE cannot be calculated without expense records.")

    return ValidationResult(
        is_valid=score >= PASSING_SCORE,
        score=min(score, 100),
        issues=issues,
        recommendations=recommendations,
    )
