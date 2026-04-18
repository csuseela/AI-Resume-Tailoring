"""Generate smart search queries from the user's resume and profile.

Also provides curated lists of H1B-sponsoring companies and
high-growth startups to target via Greenhouse/Lever.
"""

from __future__ import annotations

import logging
import re
from typing import Any, List, Set

from app.core.config import SearchProfile

logger = logging.getLogger(__name__)

H1B_SPONSOR_COMPANIES: Set[str] = {
    "google", "meta", "amazon", "apple", "microsoft", "nvidia",
    "oracle", "salesforce", "adobe", "ibm", "intel", "cisco",
    "qualcomm", "vmware", "broadcom",
    "jpmorgan", "jpmorgan chase", "goldman sachs", "morgan stanley",
    "bank of america", "citibank", "citi", "wells fargo",
    "capital one", "american express", "barclays",
    "discover", "discover financial",
    "visa", "mastercard", "paypal", "stripe", "plaid",
    "robinhood", "sofi", "chime",
    "deloitte", "ey", "ernst & young", "pwc", "kpmg",
    "accenture", "mckinsey", "bain", "bcg", "infosys",
    "tcs", "cognizant", "wipro", "hcl", "tech mahindra",
    "snowflake", "databricks", "datadog", "confluent",
    "hashicorp", "cloudera", "palantir", "splunk",
    "elastic", "mongodb", "cockroach labs",
    "uber", "lyft", "airbnb", "doordash", "instacart",
    "pinterest", "snap", "reddit", "discord", "spotify",
    "netflix", "twitter", "x corp",
    "coinbase", "block", "square",
    "servicenow", "workday", "atlassian", "twilio",
    "zendesk", "hubspot", "figma", "notion",
    "asana", "monday.com", "airtable",
    "unitedhealth", "optum", "anthem", "humana",
    "epic", "cerner", "veeva",
    "rippling", "ramp", "brex", "gusto", "deel",
    "anduril", "scale ai", "openai", "anthropic",
    "cohere", "mistral",
}

STARTUP_GREENHOUSE_SLUGS: List[str] = [
    "stripe", "airbnb", "figma", "brex", "gusto",
    "databricks", "datadog", "anthropic",
    "coinbase", "robinhood", "chime", "discord",
    "airtable", "asana", "relativity", "cockroachlabs",
    "scaleai", "andurilindustries",
]

STARTUP_LEVER_SLUGS: List[str] = [
    "spotify", "plaid", "palantir",
]


def is_h1b_sponsor(company: str) -> bool:
    return company.strip().lower() in H1B_SPONSOR_COMPANIES


def generate_search_queries(
    profile: SearchProfile,
    resume_text: str = "",
) -> List[str]:
    queries: List[str] = []
    for role in profile.target_roles[:6]:
        queries.append(role)

    domains = _extract_domains(resume_text, profile)
    if domains:
        top_roles = profile.target_roles[:3]
        for role in top_roles:
            for domain in domains[:2]:
                queries.append(f"{role} {domain}")

    queries.append("H1B sponsorship program manager")
    queries.append("H1B sponsorship data analyst")

    seen: set = set()
    unique: List[str] = []
    for q in queries:
        key = q.lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(q)

    logger.info("Generated %d search queries from profile", len(unique))
    return unique


def _extract_domains(resume_text: str, profile: SearchProfile) -> List[str]:
    text = resume_text.lower()
    domain_map = {
        "financial services": ["financial", "finance", "banking", "fintech"],
        "healthcare": ["health", "medical", "clinical", "pharma"],
        "e-commerce": ["ecommerce", "e-commerce", "retail", "marketplace"],
        "data platform": ["data platform", "data infrastructure", "data engineering"],
    }
    found: List[str] = []
    for domain, triggers in domain_map.items():
        if any(t in text for t in triggers):
            found.append(domain)
    return found


def get_startup_greenhouse_slugs() -> List[str]:
    return STARTUP_GREENHOUSE_SLUGS.copy()


def get_startup_lever_slugs() -> List[str]:
    return STARTUP_LEVER_SLUGS.copy()
