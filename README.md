# BlackRoad CRM

> Customer Relationship Management system — SQLite-backed, zero-dependency Python.

## Features

- **Contacts** — full lifecycle: lead → prospect → customer → churned, lead scoring, tags, owner assignment
- **Deals** — 6-stage pipeline with auto-probability, weighted pipeline value
- **Activities** — call / email / meeting / demo / follow-up tracking
- **Analytics** — pipeline value, conversion funnel, win rate, activity summary
- **Export** — CSV and JSON export for contacts and deals

## Quick Start

```python
from crm import CRM, DealStage, ActivityType

crm = CRM("my_crm.db")

# Add a contact
contact = crm.add_contact("Alice Johnson", "alice@acme.com",
                           company="Acme Corp", source="linkedin",
                           tags=["enterprise"])

# Score the lead
crm.update_lead_score(contact.id, 40)

# Create a deal
deal = crm.create_deal(contact.id, "Enterprise License", 150_000,
                       DealStage.QUALIFIED, close_date="2025-03-31")

# Log activity
crm.log_activity(contact.id, ActivityType.CALL,
                 "Discovery call", outcome="Very interested")

# Advance the deal
crm.advance_deal(deal.id, DealStage.NEGOTIATION)

# Pipeline analytics
print(crm.pipeline_value())
print(crm.conversion_funnel())

# Export
csv_data = crm.export_contacts("csv")
```

## Data Model

| Model | Key Fields |
|-------|-----------|
| `Contact` | id, name, email, phone, company, title, tags, lead_score, status, owner, source |
| `Deal` | id, contact_id, title, value, stage, probability, close_date, notes |
| `Activity` | id, contact_id, type, summary, outcome, next_action, recorded_at |

## Pipeline Stages

`prospecting (10%) → qualified (25%) → proposal (50%) → negotiation (75%) → closed_won (100%) / closed_lost (0%)`

## Running Tests

```bash
pip install pytest
pytest test_crm.py -v
```

## Demo

```bash
python crm.py
```
