"""
Export Service

Exports leads to CSV, Excel (xlsx) or JSON for download (Iteration 1.6).

The CSV column order follows the development plan's export specification,
extended with Keyword/Status/City for practical reuse.
"""

import csv
import io
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Sequence, Tuple

from openpyxl import Workbook

from app.core.config import settings
from app.models.lead import Lead

logger = logging.getLogger(__name__)

# (column header, value extractor)
EXPORT_COLUMNS: Sequence[Tuple[str, Callable[[Lead], Any]]] = (
    ("Organization", lambda lead: lead.organization_name),
    ("Website", lambda lead: lead.website),
    ("Contact Name", lambda lead: lead.contact_name or ""),
    ("Job Title", lambda lead: lead.job_title or ""),
    ("Department", lambda lead: lead.department or ""),
    ("Email", lambda lead: lead.email or ""),
    ("Phone", lambda lead: lead.phone or ""),
    ("Country", lambda lead: lead.country or ""),
    ("City", lambda lead: lead.city or ""),
    ("Contact URL", lambda lead: lead.contact_page_url or ""),
    ("Source URL", lambda lead: lead.source_url),
    ("Keyword", lambda lead: lead.keyword),
    ("Status", lambda lead: lead.status),
    ("Lead Score", lambda lead: lead.lead_score),
    ("Reason", lambda lead: lead.ai_reasoning or ""),
    ("Date Found", lambda lead: lead.created_at.strftime("%Y-%m-%d") if lead.created_at else ""),
)

SUPPORTED_FORMATS = ("csv", "excel", "json")

MEDIA_TYPES: Dict[str, str] = {
    "csv": "text/csv; charset=utf-8",
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "json": "application/json",
}

EXTENSIONS: Dict[str, str] = {"csv": "csv", "excel": "xlsx", "json": "json"}


class ExportService:
    """Serializes leads into downloadable CSV / Excel / JSON payloads."""

    def export(self, leads: Sequence[Lead], export_format: str) -> Tuple[bytes, str, str]:
        """
        Export leads in the requested format.

        Args:
            leads: Leads to export.
            export_format: One of ``csv``, ``excel``, ``json``.

        Returns:
            ``(content_bytes, media_type, filename)``

        Raises:
            ValueError: If the format is not supported.
        """
        export_format = (export_format or "").lower()
        if export_format not in SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported export format {export_format!r}. "
                f"Supported: {', '.join(SUPPORTED_FORMATS)}"
            )

        max_rows = settings.max_export_size
        if len(leads) > max_rows:
            logger.warning(
                "Export truncated from %d to %d rows (max_export_size)", len(leads), max_rows
            )
            leads = leads[:max_rows]

        exporters = {
            "csv": self.to_csv,
            "excel": self.to_excel,
            "json": self.to_json,
        }
        content, media_type = exporters[export_format](leads)
        filename = f"leads_export_{datetime.utcnow():%Y%m%d_%H%M%S}.{EXTENSIONS[export_format]}"
        return content, media_type, filename

    # ------------------------------------------------------------------
    # Format serializers
    # ------------------------------------------------------------------
    def to_csv(self, leads: Sequence[Lead]) -> Tuple[bytes, str]:
        """CSV (UTF-8 with BOM so Excel opens non-ASCII names correctly)."""
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([header for header, _ in EXPORT_COLUMNS])
        for lead in leads:
            writer.writerow([extractor(lead) for _, extractor in EXPORT_COLUMNS])
        # utf-8-sig: BOM keeps Excel happy with accented characters
        return buffer.getvalue().encode("utf-8-sig"), MEDIA_TYPES["csv"]

    def to_excel(self, leads: Sequence[Lead]) -> Tuple[bytes, str]:
        """Excel workbook (xlsx) with a single Leads sheet."""
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Leads"

        sheet.append([header for header, _ in EXPORT_COLUMNS])
        for lead in leads:
            sheet.append([extractor(lead) for _, extractor in EXPORT_COLUMNS])

        buffer = io.BytesIO()
        workbook.save(buffer)
        return buffer.getvalue(), MEDIA_TYPES["excel"]

    def to_json(self, leads: Sequence[Lead]) -> Tuple[bytes, str]:
        """Pretty-printed JSON list of lead objects."""
        payload = [
            {header: extractor(lead) for header, extractor in EXPORT_COLUMNS} for lead in leads
        ]
        content = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
        return content.encode("utf-8"), MEDIA_TYPES["json"]


export_service = ExportService()
