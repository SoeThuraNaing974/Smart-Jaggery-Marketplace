"""Admin-editable grade descriptions (site_content key "grades")."""


def test_grades_default_empty(client):
    r = client.get("/api/content/grades")
    assert r.status_code == 200
    assert r.get_json() == {}


def test_admin_saves_and_public_reads(admin_client, client):
    fields = {
        "a_title": "Grade A (premium)",
        "a_quality": "Golden and pure.",
        "a_strengths": "Great taste\nHealthy",
        "b_weaknesses": "A bit plain",
    }
    r = admin_client.put("/api/admin/content/grades", json=fields)
    assert r.status_code == 200

    got = client.get("/api/content/grades").get_json()
    assert got["a_title"] == "Grade A (premium)"
    # newline-separated bullet lists survive the round trip
    assert got["a_strengths"] == "Great taste\nHealthy"
    assert got["b_weaknesses"] == "A bit plain"


def test_blank_fields_are_dropped(admin_client, client):
    admin_client.put("/api/admin/content/grades", json={"a_title": "Custom", "a_quality": "Nice"})
    # re-save with a_quality blank → only a_title remains (falls back to default)
    admin_client.put("/api/admin/content/grades", json={"a_title": "Custom", "a_quality": "   "})
    got = client.get("/api/content/grades").get_json()
    assert got == {"a_title": "Custom"}


def test_only_admin_can_save(customer_client, staff_client):
    for c in (customer_client, staff_client):
        r = c.put("/api/admin/content/grades", json={"a_title": "hijack"})
        assert r.status_code == 403


def test_unknown_key_rejected(admin_client, client):
    assert admin_client.put("/api/admin/content/nope", json={"x": "y"}).status_code == 404
    assert client.get("/api/content/nope").status_code == 404
