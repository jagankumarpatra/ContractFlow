def test_create_contract(client, auth_headers):
    res = client.post("/api/v1/contracts/", json={
        "title": "Service Agreement 2024",
        "contract_type": "service_agreement",
        "party_a": "Seller Corp",
        "party_b": "Buyer Ltd",
        "contract_text": "This agreement governs the provision of services..."
    }, headers=auth_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Service Agreement 2024"
    assert data["status"] == "draft"
    assert data["contract_type"] == "service_agreement"

def test_create_contract_minimal(client, auth_headers):
    res = client.post("/api/v1/contracts/", json={
        "title": "Simple Contract"
    }, headers=auth_headers)
    assert res.status_code == 201

def test_create_contract_unauthenticated(client):
    res = client.post("/api/v1/contracts/", json={"title": "Test"})
    assert res.status_code == 403

def test_get_contract(client, auth_headers, sample_contract):
    res = client.get(f"/api/v1/contracts/{sample_contract['id']}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["id"] == sample_contract["id"]

def test_get_nonexistent_contract(client, auth_headers):
    res = client.get("/api/v1/contracts/nonexistent-id", headers=auth_headers)
    assert res.status_code == 404

def test_list_contracts(client, auth_headers, sample_contract):
    res = client.get("/api/v1/contracts/", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert len(data["contracts"]) >= 1
    assert data["page"] == 1

def test_list_contracts_pagination(client, auth_headers):
    for i in range(3):
        client.post("/api/v1/contracts/", json={"title": f"Contract {i}"}, headers=auth_headers)
    res = client.get("/api/v1/contracts/?page=1&limit=2", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()["contracts"]) <= 2

def test_list_contracts_filter_by_status(client, auth_headers, sample_contract):
    res = client.get("/api/v1/contracts/?status=draft", headers=auth_headers)
    assert res.status_code == 200
    for c in res.json()["contracts"]:
        assert c["status"] == "draft"

def test_list_contracts_search(client, auth_headers):
    client.post("/api/v1/contracts/", json={
        "title": "ACME Partnership Deal", "party_a": "ACME Corp"
    }, headers=auth_headers)
    res = client.get("/api/v1/contracts/?search=ACME", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["total"] >= 1

def test_update_contract(client, auth_headers, sample_contract):
    res = client.patch(f"/api/v1/contracts/{sample_contract['id']}",
                      json={"title": "Updated NDA Agreement"},
                      headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["title"] == "Updated NDA Agreement"

def test_valid_status_transition(client, auth_headers, sample_contract):
    # draft → under_review
    res = client.patch(f"/api/v1/contracts/{sample_contract['id']}/status",
                      json={"status": "under_review"}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "under_review"

def test_invalid_status_transition(client, auth_headers, sample_contract):
    # draft → signed (invalid — must go through review first)
    res = client.patch(f"/api/v1/contracts/{sample_contract['id']}/status",
                      json={"status": "signed"}, headers=auth_headers)
    assert res.status_code == 400

def test_full_status_workflow(client, auth_headers, sample_contract):
    cid = sample_contract["id"]
    steps = [
        ("under_review", 200),
        ("approved", 200),
        ("signed", 200),
    ]
    for status, expected_code in steps:
        res = client.patch(f"/api/v1/contracts/{cid}/status",
                          json={"status": status}, headers=auth_headers)
        assert res.status_code == expected_code, f"Failed at transition to {status}: {res.json()}"
        assert res.json()["status"] == status

def test_delete_draft_contract(client, auth_headers):
    res = client.post("/api/v1/contracts/", json={"title": "To Delete"}, headers=auth_headers)
    cid = res.json()["id"]
    del_res = client.delete(f"/api/v1/contracts/{cid}", headers=auth_headers)
    assert del_res.status_code == 204

def test_cannot_delete_signed_contract(client, auth_headers, sample_contract):
    cid = sample_contract["id"]
    for status in ["under_review", "approved", "signed"]:
        client.patch(f"/api/v1/contracts/{cid}/status",
                    json={"status": status}, headers=auth_headers)
    res = client.delete(f"/api/v1/contracts/{cid}", headers=auth_headers)
    assert res.status_code == 400

def test_tenant_isolation(client):
    # User from Company A cannot see Company B's contracts
    client.post("/api/v1/auth/register", json={
        "name": "User A", "email": "a@company.com",
        "password": "pass123", "company_name": "Company A"
    })
    res_b = client.post("/api/v1/auth/register", json={
        "name": "User B", "email": "b@company.com",
        "password": "pass123", "company_name": "Company B"
    })
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Create contract as User A
    res_a = client.post("/api/v1/auth/login", json={"email": "a@company.com", "password": "pass123"})
    headers_a = {"Authorization": f"Bearer {res_a.json()['access_token']}"}
    contract = client.post("/api/v1/contracts/", json={"title": "Secret Contract A"},
                          headers=headers_a).json()

    # Try to access as User B
    res = client.get(f"/api/v1/contracts/{contract['id']}", headers=headers_b)
    assert res.status_code == 404  # Not found (isolated by tenant)

def test_ai_analysis_trigger(client, auth_headers):
    res = client.post("/api/v1/contracts/", json={
        "title": "AI Test Contract",
        "contract_text": "This agreement is between Party A and Party B for software services."
    }, headers=auth_headers)
    assert res.status_code == 201
    cid = res.json()["id"]

    # Manually trigger analysis
    res2 = client.post(f"/api/v1/contracts/{cid}/analyze", headers=auth_headers)
    assert res2.status_code == 200
