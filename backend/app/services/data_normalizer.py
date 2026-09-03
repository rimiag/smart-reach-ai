"""
Data Normalizer

Cleans and normalizes crawler-extracted contact data before it is written to
the leads table: website URL scheme, organization-name fallback derived from
the domain, email/phone cleanup and de-duplication.
"""

import logging
import re
from typing import List

from app.crawlers.email_extractor import is_likely_junk
from app.integrations.search_base import extract_domain
from app.schemas.contact_info import ContactInfo

logger = logging.getLogger(__name__)


class DataNormalizer:
    """Normalizes ContactInfo records before lead creation."""

    def normalize(self, contact: ContactInfo, fallback_domain: str = "") -> ContactInfo:
        """
        Return a cleaned copy of ``contact``.

        Args:
            contact: Raw extraction result.
            fallback_domain: Domain used to derive the organization name when
                none was found on the site.
        """
        website = self.normalize_website(contact.website)

        organization_name = (contact.organization_name or "").strip()
        if not organization_name:
            organization_name = self.organization_from_domain(fallback_domain or website)

        emails: List[str] = []
        for email in contact.emails:
            cleaned = email.strip().lower()
            if cleaned and cleaned not in emails and not is_likely_junk(cleaned):
                emails.append(cleaned)

        phones: List[str] = []
        for phone in contact.phones:
            cleaned = re.sub(r"\s+", " ", phone.strip())
            if cleaned and cleaned not in phones:
                phones.append(cleaned)

        return contact.model_copy(
            update={
                "website": website,
                "organization_name": organization_name[:255],
                "emails": emails,
                "phones": phones,
            }
        )

    @staticmethod
    def normalize_website(website: str) -> str:
        """Ensure the website is an absolute http(s) URL."""
        website = (website or "").strip()
        if not website:
            return website
        if not website.lower().startswith(("http://", "https://")):
            return f"https://{website.lstrip('/')}"
        return website

    @staticmethod
    def organization_from_domain(domain_or_url: str) -> str:
        """Derive a display name from a domain: acme-tools.com -> Acme Tools."""
        domain = extract_domain(domain_or_url) or domain_or_url.strip()
        labels = [label for label in domain.split(".") if label and label != "www"]
        if not labels:
            return domain.title()
        name = labels[0].replace("-", " ").replace("_", " ")
        return name.title() if name else domain.title()


data_normalizer = DataNormalizer()
