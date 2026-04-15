from app.services.llm_service import LLMService
from app.services.resume_tailor import ResumeTailorService


def test_llm_json_parser_accepts_markdown_fenced_json() -> None:
    raw = """```json
{
  "summary": "Test summary",
  "skills": "Python, SQL",
  "experience_bullets": {"Experience": ["Built things", "Led teams"]},
  "fit_score": 85.0,
  "one_line_reason": "Great fit"
}
```"""
    result = LLMService.parse_structured_output(raw)
    assert result.summary == "Test summary"
    assert result.fit_score == 85.0


def test_resume_tailor_merges_only_targeted_sections() -> None:
    master = """# Name

## Summary
Old summary text.

## Skills
Old skills.

## Experience
- Old bullet 1
"""
    raw_json = """{
      "summary": "New summary text.",
      "skills": "Python, SQL, Tableau",
      "experience_bullets": {},
      "fit_score": 80.0,
      "one_line_reason": "Good fit"
    }"""

    llm = LLMService.parse_structured_output(raw_json)
    tailored, ats_score = ResumeTailorService().tailor(master, llm)

    assert "New summary text." in tailored
    assert "Python, SQL, Tableau" in tailored
    assert "# Name" in tailored
