"""pytest tests for BlackRoad CRM"""
import os, tempfile, pytest
from crm import (CRM, ContactStatus, DealStage, ActivityType)


@pytest.fixture
def crm(tmp_path):
    c = CRM(str(tmp_path / "test.db"))
    yield c
    c.close()


def test_add_contact(crm):
    c = crm.add_contact("Alice", "alice@test.com", company="Acme")
    assert c.id
    assert c.name == "Alice"
    assert c.status == ContactStatus.LEAD

def test_duplicate_email_raises(crm):
    crm.add_contact("Alice", "dup@test.com")
    with pytest.raises(ValueError):
        crm.add_contact("Alice2", "dup@test.com")

def test_update_lead_score(crm):
    c = crm.add_contact("Bob", "bob@test.com")
    new = crm.update_lead_score(c.id, 50)
    assert new == 50
    new2 = crm.update_lead_score(c.id, -10)
    assert new2 == 40

def test_lead_score_floor(crm):
    c = crm.add_contact("Carol", "carol@test.com")
    score = crm.update_lead_score(c.id, -999)
    assert score == 0

def test_create_deal(crm):
    c = crm.add_contact("Dave", "dave@test.com")
    d = crm.create_deal(c.id, "Big Deal", 100_000, DealStage.QUALIFIED)
    assert d.id
    assert d.value == 100_000
    assert d.probability == 0.25

def test_advance_deal(crm):
    c = crm.add_contact("Eve", "eve@test.com")
    d = crm.create_deal(c.id, "Deal", 50_000)
    updated = crm.advance_deal(d.id, DealStage.CLOSED_WON)
    assert updated.stage == DealStage.CLOSED_WON
    assert updated.probability == 1.0

def test_log_activity(crm):
    c = crm.add_contact("Frank", "frank@test.com")
    a = crm.log_activity(c.id, ActivityType.CALL, "Discovery call", "Positive")
    assert a.id
    activities = crm.list_activities(c.id)
    assert len(activities) == 1
    assert activities[0].type == ActivityType.CALL

def test_pipeline_value(crm):
    c = crm.add_contact("Grace", "grace@test.com")
    crm.create_deal(c.id, "Deal1", 100_000, DealStage.PROSPECTING)
    crm.create_deal(c.id, "Deal2", 50_000, DealStage.CLOSED_WON)
    pv = crm.pipeline_value()
    assert pv["total_pipeline"] == 150_000.0

def test_conversion_funnel(crm):
    crm.add_contact("H", "h@test.com", status=ContactStatus.LEAD)
    crm.add_contact("I", "i@test.com", status=ContactStatus.CUSTOMER)
    funnel = crm.conversion_funnel()
    assert funnel["total_contacts"] == 2
    assert funnel["customer"] == 1

def test_export_csv(crm):
    crm.add_contact("Jack", "jack@test.com")
    csv_data = crm.export_contacts("csv")
    assert "jack@test.com" in csv_data

def test_export_json(crm):
    import json
    crm.add_contact("Jill", "jill@test.com")
    json_data = crm.export_contacts("json")
    data = json.loads(json_data)
    assert any(c["email"] == "jill@test.com" for c in data)

def test_list_contacts_filter(crm):
    crm.add_contact("K", "k@test.com", status=ContactStatus.CUSTOMER)
    crm.add_contact("L", "l@test.com", status=ContactStatus.LEAD)
    customers = crm.list_contacts(status=ContactStatus.CUSTOMER)
    assert len(customers) == 1

def test_deal_not_found(crm):
    result = crm.advance_deal("nonexistent", DealStage.PROPOSAL)
    assert result is None
