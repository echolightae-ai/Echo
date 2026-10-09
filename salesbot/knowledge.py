"""Loads the business facts and price list the agent is allowed to use."""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def load_business_facts(knowledge_dir: Path) -> str:
    text = (knowledge_dir / "business.md").read_text(encoding="utf-8")
    return _COMMENT.sub("", text).strip()


@dataclass(frozen=True)
class PriceList:
    vat_rate: float
    validity_days: int
    max_discount_percent: float
    services: dict[str, dict]

    @classmethod
    def load(cls, knowledge_dir: Path) -> "PriceList":
        data = yaml.safe_load((knowledge_dir / "pricing.yaml").read_text(encoding="utf-8")) or {}
        return cls(
            vat_rate=float(data.get("vat_rate", 0.05)),
            validity_days=int(data.get("quote_validity_days", 14)),
            max_discount_percent=float(data.get("max_discount_percent", 0)),
            services=data.get("services") or {},
        )

    def catalogue(self) -> str:
        """One line per service, for the agent's instructions."""
        lines = []
        for service_id, s in self.services.items():
            priced = s.get("min") is not None and s.get("max") is not None
            status = "priced" if priced else "not priced - team quotes manually"
            lines.append(f"- {service_id}: {s.get('label', service_id)} (unit: {s.get('unit', 'item')}; {status})")
        return "\n".join(lines)

    def estimate(self, items: list[dict]) -> dict:
        """Indicative range for a list of {service_id, quantity, days}. Never invents a price."""
        lines, unpriced, unknown = [], [], []
        total_min = total_max = 0.0
        for item in items:
            service_id = item["service_id"]
            service = self.services.get(service_id)
            if service is None:
                unknown.append(service_id)
                continue
            if service.get("min") is None or service.get("max") is None:
                unpriced.append(service_id)
                continue
            multiplier = max(float(item.get("quantity") or 1), 0) * max(float(item.get("days") or 1), 0)
            low, high = float(service["min"]) * multiplier, float(service["max"]) * multiplier
            total_min += low
            total_max += high
            lines.append({"service_id": service_id, "label": service.get("label"), "min_aed": round(low), "max_aed": round(high)})
        return {
            "lines": lines,
            "subtotal_min_aed": round(total_min),
            "subtotal_max_aed": round(total_max),
            "vat_rate": self.vat_rate,
            "total_min_incl_vat_aed": round(total_min * (1 + self.vat_rate)),
            "total_max_incl_vat_aed": round(total_max * (1 + self.vat_rate)),
            "valid_days": self.validity_days,
            "not_priced": unpriced,
            "unknown_services": unknown,
        }
