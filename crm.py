"""
BlackRoad CRM - Customer Relationship Management System
SQLite-backed CRM with contacts, deals, activities, pipeline analytics.
"""

import sqlite3
import json
import csv
import io
import uuid
from datetime import datetime, date
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum
from pathlib import Path


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ContactStatus(str, Enum):
    LEAD = "lead"
    PROSPECT = "prospect"
    CUSTOMER = "customer"
    CHURNED = "churned"


class DealStage(str, Enum):
    PROSPECTING = "prospecting"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class ActivityType(str, Enum):
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    DEMO = "demo"
    FOLLOW_UP = "follow_up"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Contact:
    id: str
    name: str
    email: str
    phone: str = ""
    company: str = ""
    title: str = ""
    tags: List[str] = field(default_factory=list)
    lead_score: int = 0
    status: ContactStatus = ContactStatus.LEAD
    owner: str = ""
    source: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_contact: Optional[str] = None


@dataclass
class Deal:
    id: str
    contact_id: str
    title: str
    value: float
    stage: DealStage = DealStage.PROSPECTING
    probability: float = 0.0
    close_date: Optional[str] = None
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class Activity:
    id: str
    contact_id: str
    type: ActivityType
    summary: str
    outcome: str = ""
    next_action: str = ""
    recorded_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ---------------------------------------------------------------------------
# Stage probability defaults
# ---------------------------------------------------------------------------

STAGE_PROBABILITY: Dict[DealStage, float] = {
    DealStage.PROSPECTING: 0.10,
    DealStage.QUALIFIED: 0.25,
    DealStage.PROPOSAL: 0.50,
    DealStage.NEGOTIATION: 0.75,
    DealStage.CLOSED_WON: 1.00,
    DealStage.CLOSED_LOST: 0.00,
}


# ---------------------------------------------------------------------------
# Database layer
# ---------------------------------------------------------------------------

class CRMDatabase:
    """SQLite persistence layer for the CRM."""

    def __init__(self, db_path: str = "crm.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self.conn:
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id          TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    email       TEXT UNIQUE NOT NULL,
                    phone       TEXT DEFAULT '',
                    company     TEXT DEFAULT '',
                    title       TEXT DEFAULT '',
                    tags        TEXT DEFAULT '[]',
                    lead_score  INTEGER DEFAULT 0,
                    status      TEXT DEFAULT 'lead',
                    owner       TEXT DEFAULT '',
                    source      TEXT DEFAULT '',
                    created_at  TEXT NOT NULL,
                    last_contact TEXT
                );

                CREATE TABLE IF NOT EXISTS deals (
                    id          TEXT PRIMARY KEY,
                    contact_id  TEXT NOT NULL REFERENCES contacts(id),
                    title       TEXT NOT NULL,
                    value       REAL NOT NULL DEFAULT 0,
                    stage       TEXT DEFAULT 'prospecting',
                    probability REAL DEFAULT 0.10,
                    close_date  TEXT,
                    notes       TEXT DEFAULT '',
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS activities (
                    id          TEXT PRIMARY KEY,
                    contact_id  TEXT NOT NULL REFERENCES contacts(id),
                    type        TEXT NOT NULL,
                    summary     TEXT NOT NULL,
                    outcome     TEXT DEFAULT '',
                    next_action TEXT DEFAULT '',
                    recorded_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_deals_contact ON deals(contact_id);
                CREATE INDEX IF NOT EXISTS idx_activities_contact ON activities(contact_id);
                CREATE INDEX IF NOT EXISTS idx_contacts_status ON contacts(status);
                CREATE INDEX IF NOT EXISTS idx_deals_stage ON deals(stage);
            """)

    def close(self) -> None:
        self.conn.close()


# ---------------------------------------------------------------------------
# CRM Service
# ---------------------------------------------------------------------------

class CRM:
    """Main CRM service exposing all business operations."""

    def __init__(self, db_path: str = "crm.db"):
        self.db = CRMDatabase(db_path)
        self.conn = self.db.conn

    # -----------------------------------------------------------------------
    # Contact operations
    # -----------------------------------------------------------------------

    def add_contact(
        self,
        name: str,
        email: str,
        phone: str = "",
        company: str = "",
        title: str = "",
        tags: Optional[List[str]] = None,
        owner: str = "",
        source: str = "",
        status: ContactStatus = ContactStatus.LEAD,
    ) -> Contact:
        """Create a new contact. Raises ValueError on duplicate email."""
        existing = self.get_contact_by_email(email)
        if existing:
            raise ValueError(f"Contact with email '{email}' already exists (id={existing.id})")

        contact = Contact(
            id=str(uuid.uuid4()),
            name=name,
            email=email,
            phone=phone,
            company=company,
            title=title,
            tags=tags or [],
            owner=owner,
            source=source,
            status=status,
        )
        with self.conn:
            self.conn.execute(
                """INSERT INTO contacts
                   (id, name, email, phone, company, title, tags, lead_score,
                    status, owner, source, created_at, last_contact)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    contact.id, contact.name, contact.email, contact.phone,
                    contact.company, contact.title, json.dumps(contact.tags),
                    contact.lead_score, contact.status.value, contact.owner,
                    contact.source, contact.created_at, contact.last_contact,
                ),
            )
        return contact

    def get_contact(self, contact_id: str) -> Optional[Contact]:
        row = self.conn.execute(
            "SELECT * FROM contacts WHERE id = ?", (contact_id,)
        ).fetchone()
        return self._row_to_contact(row) if row else None

    def get_contact_by_email(self, email: str) -> Optional[Contact]:
        row = self.conn.execute(
            "SELECT * FROM contacts WHERE email = ?", (email,)
        ).fetchone()
        return self._row_to_contact(row) if row else None

    def list_contacts(
        self,
        status: Optional[ContactStatus] = None,
        owner: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[Contact]:
        query = "SELECT * FROM contacts WHERE 1=1"
        params: List[Any] = []
        if status:
            query += " AND status = ?"
            params.append(status.value)
        if owner:
            query += " AND owner = ?"
            params.append(owner)
        rows = self.conn.execute(query, params).fetchall()
        contacts = [self._row_to_contact(r) for r in rows]
        if tag:
            contacts = [c for c in contacts if tag in c.tags]
        return contacts

    def update_contact(self, contact_id: str, **kwargs) -> Optional[Contact]:
        """Partial update of a contact's fields."""
        contact = self.get_contact(contact_id)
        if not contact:
            return None
        allowed = {
            "name", "phone", "company", "title", "tags",
            "owner", "source", "status", "last_contact",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return contact
        set_clauses = []
        vals: List[Any] = []
        for k, v in updates.items():
            set_clauses.append(f"{k} = ?")
            vals.append(json.dumps(v) if k == "tags" else (v.value if isinstance(v, Enum) else v))
        vals.append(contact_id)
        with self.conn:
            self.conn.execute(
                f"UPDATE contacts SET {', '.join(set_clauses)} WHERE id = ?", vals
            )
        return self.get_contact(contact_id)

    def update_lead_score(self, contact_id: str, delta: int) -> int:
        """Adjust the lead score by delta (can be negative). Returns new score."""
        contact = self.get_contact(contact_id)
        if not contact:
            raise ValueError(f"Contact {contact_id} not found")
        new_score = max(0, contact.lead_score + delta)
        with self.conn:
            self.conn.execute(
                "UPDATE contacts SET lead_score = ? WHERE id = ?",
                (new_score, contact_id),
            )
        return new_score

    def delete_contact(self, contact_id: str) -> bool:
        with self.conn:
            cursor = self.conn.execute(
                "DELETE FROM contacts WHERE id = ?", (contact_id,)
            )
        return cursor.rowcount > 0

    # -----------------------------------------------------------------------
    # Deal operations
    # -----------------------------------------------------------------------

    def create_deal(
        self,
        contact_id: str,
        title: str,
        value: float,
        stage: DealStage = DealStage.PROSPECTING,
        close_date: Optional[str] = None,
        notes: str = "",
    ) -> Deal:
        """Create a new deal linked to a contact."""
        if not self.get_contact(contact_id):
            raise ValueError(f"Contact {contact_id} not found")
        now = datetime.utcnow().isoformat()
        deal = Deal(
            id=str(uuid.uuid4()),
            contact_id=contact_id,
            title=title,
            value=value,
            stage=stage,
            probability=STAGE_PROBABILITY[stage],
            close_date=close_date,
            notes=notes,
            created_at=now,
            updated_at=now,
        )
        with self.conn:
            self.conn.execute(
                """INSERT INTO deals
                   (id, contact_id, title, value, stage, probability,
                    close_date, notes, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    deal.id, deal.contact_id, deal.title, deal.value,
                    deal.stage.value, deal.probability, deal.close_date,
                    deal.notes, deal.created_at, deal.updated_at,
                ),
            )
        return deal

    def get_deal(self, deal_id: str) -> Optional[Deal]:
        row = self.conn.execute(
            "SELECT * FROM deals WHERE id = ?", (deal_id,)
        ).fetchone()
        return self._row_to_deal(row) if row else None

    def list_deals(
        self,
        contact_id: Optional[str] = None,
        stage: Optional[DealStage] = None,
    ) -> List[Deal]:
        query = "SELECT * FROM deals WHERE 1=1"
        params: List[Any] = []
        if contact_id:
            query += " AND contact_id = ?"
            params.append(contact_id)
        if stage:
            query += " AND stage = ?"
            params.append(stage.value)
        rows = self.conn.execute(query, params).fetchall()
        return [self._row_to_deal(r) for r in rows]

    def advance_deal(self, deal_id: str, new_stage: DealStage) -> Optional[Deal]:
        """Move a deal to a new stage, updating probability automatically."""
        deal = self.get_deal(deal_id)
        if not deal:
            return None
        now = datetime.utcnow().isoformat()
        prob = STAGE_PROBABILITY[new_stage]
        with self.conn:
            self.conn.execute(
                "UPDATE deals SET stage = ?, probability = ?, updated_at = ? WHERE id = ?",
                (new_stage.value, prob, now, deal_id),
            )
        return self.get_deal(deal_id)

    def update_deal(self, deal_id: str, **kwargs) -> Optional[Deal]:
        deal = self.get_deal(deal_id)
        if not deal:
            return None
        allowed = {"title", "value", "close_date", "notes", "probability"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return deal
        updates["updated_at"] = datetime.utcnow().isoformat()
        set_clauses = [f"{k} = ?" for k in updates]
        vals = list(updates.values()) + [deal_id]
        with self.conn:
            self.conn.execute(
                f"UPDATE deals SET {', '.join(set_clauses)} WHERE id = ?", vals
            )
        return self.get_deal(deal_id)

    # -----------------------------------------------------------------------
    # Activity operations
    # -----------------------------------------------------------------------

    def log_activity(
        self,
        contact_id: str,
        activity_type: ActivityType,
        summary: str,
        outcome: str = "",
        next_action: str = "",
    ) -> Activity:
        """Record a sales activity against a contact."""
        if not self.get_contact(contact_id):
            raise ValueError(f"Contact {contact_id} not found")
        now = datetime.utcnow().isoformat()
        activity = Activity(
            id=str(uuid.uuid4()),
            contact_id=contact_id,
            type=activity_type,
            summary=summary,
            outcome=outcome,
            next_action=next_action,
            recorded_at=now,
        )
        with self.conn:
            self.conn.execute(
                """INSERT INTO activities
                   (id, contact_id, type, summary, outcome, next_action, recorded_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    activity.id, activity.contact_id, activity.type.value,
                    activity.summary, activity.outcome, activity.next_action,
                    activity.recorded_at,
                ),
            )
            self.conn.execute(
                "UPDATE contacts SET last_contact = ? WHERE id = ?",
                (now, contact_id),
            )
        return activity

    def list_activities(self, contact_id: str) -> List[Activity]:
        rows = self.conn.execute(
            "SELECT * FROM activities WHERE contact_id = ? ORDER BY recorded_at DESC",
            (contact_id,),
        ).fetchall()
        return [self._row_to_activity(r) for r in rows]

    # -----------------------------------------------------------------------
    # Analytics
    # -----------------------------------------------------------------------

    def pipeline_value(self) -> Dict[str, Any]:
        """Weighted and total pipeline value broken down by stage."""
        rows = self.conn.execute(
            "SELECT stage, SUM(value) as total, SUM(value*probability) as weighted, COUNT(*) as count FROM deals GROUP BY stage"
        ).fetchall()
        stages = {}
        total_value = 0.0
        weighted_value = 0.0
        for r in rows:
            stages[r["stage"]] = {
                "total": round(r["total"], 2),
                "weighted": round(r["weighted"], 2),
                "count": r["count"],
            }
            total_value += r["total"]
            weighted_value += r["weighted"]
        return {
            "by_stage": stages,
            "total_pipeline": round(total_value, 2),
            "weighted_pipeline": round(weighted_value, 2),
        }

    def conversion_funnel(self) -> Dict[str, Any]:
        """Contact funnel: lead → prospect → customer, with conversion rates."""
        rows = self.conn.execute(
            "SELECT status, COUNT(*) as count FROM contacts GROUP BY status"
        ).fetchall()
        counts = {r["status"]: r["count"] for r in rows}
        lead = counts.get("lead", 0)
        prospect = counts.get("prospect", 0)
        customer = counts.get("customer", 0)
        churned = counts.get("churned", 0)
        total = lead + prospect + customer + churned
        return {
            "total_contacts": total,
            "lead": lead,
            "prospect": prospect,
            "customer": customer,
            "churned": churned,
            "lead_to_prospect_rate": round(prospect / lead, 3) if lead else 0,
            "prospect_to_customer_rate": round(customer / prospect, 3) if prospect else 0,
            "overall_conversion_rate": round(customer / total, 3) if total else 0,
        }

    def deal_win_rate(self) -> Dict[str, float]:
        """Win rate by stage progression."""
        won = self.conn.execute(
            "SELECT COUNT(*) FROM deals WHERE stage = 'closed_won'"
        ).fetchone()[0]
        lost = self.conn.execute(
            "SELECT COUNT(*) FROM deals WHERE stage = 'closed_lost'"
        ).fetchone()[0]
        total_closed = won + lost
        return {
            "closed_won": won,
            "closed_lost": lost,
            "win_rate": round(won / total_closed, 3) if total_closed else 0,
        }

    def top_contacts_by_score(self, limit: int = 10) -> List[Contact]:
        rows = self.conn.execute(
            "SELECT * FROM contacts ORDER BY lead_score DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_contact(r) for r in rows]

    def activity_summary(self) -> Dict[str, int]:
        rows = self.conn.execute(
            "SELECT type, COUNT(*) as count FROM activities GROUP BY type"
        ).fetchall()
        return {r["type"]: r["count"] for r in rows}

    # -----------------------------------------------------------------------
    # Export
    # -----------------------------------------------------------------------

    def export_contacts(self, format: str = "csv") -> str:
        """Export all contacts as CSV or JSON string."""
        contacts = self.list_contacts()
        if format == "json":
            data = []
            for c in contacts:
                d = asdict(c)
                d["status"] = c.status.value
                data.append(d)
            return json.dumps(data, indent=2)
        # CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "name", "email", "phone", "company", "title",
            "tags", "lead_score", "status", "owner", "source",
            "created_at", "last_contact",
        ])
        for c in contacts:
            writer.writerow([
                c.id, c.name, c.email, c.phone, c.company, c.title,
                "|".join(c.tags), c.lead_score, c.status.value,
                c.owner, c.source, c.created_at, c.last_contact or "",
            ])
        return output.getvalue()

    def export_deals(self, format: str = "csv") -> str:
        """Export all deals as CSV or JSON string."""
        deals = self.list_deals()
        if format == "json":
            data = []
            for d in deals:
                rec = asdict(d)
                rec["stage"] = d.stage.value
                data.append(rec)
            return json.dumps(data, indent=2)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "contact_id", "title", "value", "stage",
            "probability", "close_date", "notes", "created_at", "updated_at",
        ])
        for d in deals:
            writer.writerow([
                d.id, d.contact_id, d.title, d.value, d.stage.value,
                d.probability, d.close_date or "", d.notes,
                d.created_at, d.updated_at,
            ])
        return output.getvalue()

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _row_to_contact(self, row: sqlite3.Row) -> Contact:
        return Contact(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            phone=row["phone"],
            company=row["company"],
            title=row["title"],
            tags=json.loads(row["tags"]),
            lead_score=row["lead_score"],
            status=ContactStatus(row["status"]),
            owner=row["owner"],
            source=row["source"],
            created_at=row["created_at"],
            last_contact=row["last_contact"],
        )

    def _row_to_deal(self, row: sqlite3.Row) -> Deal:
        return Deal(
            id=row["id"],
            contact_id=row["contact_id"],
            title=row["title"],
            value=row["value"],
            stage=DealStage(row["stage"]),
            probability=row["probability"],
            close_date=row["close_date"],
            notes=row["notes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _row_to_activity(self, row: sqlite3.Row) -> Activity:
        return Activity(
            id=row["id"],
            contact_id=row["contact_id"],
            type=ActivityType(row["type"]),
            summary=row["summary"],
            outcome=row["outcome"],
            next_action=row["next_action"],
            recorded_at=row["recorded_at"],
        )

    def close(self) -> None:
        self.db.close()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _print_section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def demo() -> None:
    """Quick demo of the CRM system."""
    import tempfile, os
    db_file = tempfile.mktemp(suffix=".db")
    crm = CRM(db_file)

    _print_section("Adding Contacts")
    alice = crm.add_contact("Alice Johnson", "alice@acme.com", company="Acme Corp",
                             title="VP Sales", source="linkedin", tags=["enterprise"])
    bob = crm.add_contact("Bob Smith", "bob@startup.io", company="StartupCo",
                           title="CTO", source="referral", tags=["startup", "tech"])
    carol = crm.add_contact("Carol Williams", "carol@bigco.com", company="BigCo",
                              title="Director", source="cold_outreach", tags=["enterprise"])
    print(f"  Added: {alice.name}, {bob.name}, {carol.name}")

    _print_section("Lead Scoring")
    score = crm.update_lead_score(alice.id, 45)
    print(f"  Alice lead score: {score}")
    score = crm.update_lead_score(bob.id, 30)
    print(f"  Bob lead score:   {score}")

    _print_section("Creating Deals")
    d1 = crm.create_deal(alice.id, "Enterprise License Q1", 150_000, DealStage.QUALIFIED, "2025-03-31")
    d2 = crm.create_deal(bob.id, "SaaS Subscription", 24_000, DealStage.PROPOSAL, "2025-02-28")
    d3 = crm.create_deal(carol.id, "Consulting Project", 45_000, DealStage.NEGOTIATION)
    print(f"  Deals created: {d1.title}, {d2.title}, {d3.title}")

    _print_section("Advancing Deals")
    crm.advance_deal(d1.id, DealStage.NEGOTIATION)
    crm.advance_deal(d2.id, DealStage.CLOSED_WON)
    print("  Deal 1 → Negotiation, Deal 2 → Closed Won")

    _print_section("Logging Activities")
    crm.log_activity(alice.id, ActivityType.CALL, "Discovery call", "Interested in Q2 deal", "Send proposal")
    crm.log_activity(bob.id, ActivityType.DEMO, "Product demo", "Very positive", "Follow-up next week")
    crm.log_activity(carol.id, ActivityType.EMAIL, "Intro email", "Awaiting response")
    print("  Activities logged")

    _print_section("Pipeline Value")
    pv = crm.pipeline_value()
    print(f"  Total pipeline:    ${pv['total_pipeline']:,.2f}")
    print(f"  Weighted pipeline: ${pv['weighted_pipeline']:,.2f}")
    for stage, data in pv["by_stage"].items():
        print(f"    {stage}: ${data['total']:,.2f} ({data['count']} deals)")

    _print_section("Conversion Funnel")
    funnel = crm.conversion_funnel()
    print(f"  Total contacts: {funnel['total_contacts']}")
    print(f"  Lead → Prospect rate: {funnel['lead_to_prospect_rate']:.1%}")
    print(f"  Overall conversion:   {funnel['overall_conversion_rate']:.1%}")

    _print_section("CSV Export (first 200 chars)")
    csv_data = crm.export_contacts("csv")
    print(csv_data[:200])

    crm.close()
    os.unlink(db_file)
    print("\n✓ Demo complete")


if __name__ == "__main__":
    demo()
