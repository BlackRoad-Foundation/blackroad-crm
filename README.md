<!-- BlackRoad SEO Enhanced -->

# ulackroad crm

> Part of **[BlackRoad OS](https://blackroad.io)** — Sovereign Computing for Everyone

[![BlackRoad OS](https://img.shields.io/badge/BlackRoad-OS-ff1d6c?style=for-the-badge)](https://blackroad.io)
[![BlackRoad Foundation](https://img.shields.io/badge/Org-BlackRoad-Foundation-2979ff?style=for-the-badge)](https://github.com/BlackRoad-Foundation)
[![License](https://img.shields.io/badge/License-Proprietary-f5a623?style=for-the-badge)](LICENSE)

**ulackroad crm** is part of the **BlackRoad OS** ecosystem — a sovereign, distributed operating system built on edge computing, local AI, and mesh networking by **BlackRoad OS, Inc.**

## About BlackRoad OS

BlackRoad OS is a sovereign computing platform that runs AI locally on your own hardware. No cloud dependencies. No API keys. No surveillance. Built by [BlackRoad OS, Inc.](https://github.com/BlackRoad-OS-Inc), a Delaware C-Corp founded in 2025.

### Key Features
- **Local AI** — Run LLMs on Raspberry Pi, Hailo-8, and commodity hardware
- **Mesh Networking** — WireGuard VPN, NATS pub/sub, peer-to-peer communication
- **Edge Computing** — 52 TOPS of AI acceleration across a Pi fleet
- **Self-Hosted Everything** — Git, DNS, storage, CI/CD, chat — all sovereign
- **Zero Cloud Dependencies** — Your data stays on your hardware

### The BlackRoad Ecosystem
| Organization | Focus |
|---|---|
| [BlackRoad OS](https://github.com/BlackRoad-OS) | Core platform and applications |
| [BlackRoad OS, Inc.](https://github.com/BlackRoad-OS-Inc) | Corporate and enterprise |
| [BlackRoad AI](https://github.com/BlackRoad-AI) | Artificial intelligence and ML |
| [BlackRoad Hardware](https://github.com/BlackRoad-Hardware) | Edge hardware and IoT |
| [BlackRoad Security](https://github.com/BlackRoad-Security) | Cybersecurity and auditing |
| [BlackRoad Quantum](https://github.com/BlackRoad-Quantum) | Quantum computing research |
| [BlackRoad Agents](https://github.com/BlackRoad-Agents) | Autonomous AI agents |
| [BlackRoad Network](https://github.com/BlackRoad-Network) | Mesh and distributed networking |
| [BlackRoad Education](https://github.com/BlackRoad-Education) | Learning and tutoring platforms |
| [BlackRoad Labs](https://github.com/BlackRoad-Labs) | Research and experiments |
| [BlackRoad Cloud](https://github.com/BlackRoad-Cloud) | Self-hosted cloud infrastructure |
| [BlackRoad Forge](https://github.com/BlackRoad-Forge) | Developer tools and utilities |

### Links
- **Website**: [blackroad.io](https://blackroad.io)
- **Documentation**: [docs.blackroad.io](https://docs.blackroad.io)
- **Chat**: [chat.blackroad.io](https://chat.blackroad.io)
- **Search**: [search.blackroad.io](https://search.blackroad.io)

---


> Customer relationship management system

Part of the [BlackRoad OS](https://blackroad.io) ecosystem — [BlackRoad-Foundation](https://github.com/BlackRoad-Foundation)

---

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
