from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import UserRole
from app.services.user_service import create_user


def _create_user_and_login(
    client: TestClient,
    db_session: Session,
    *,
    email: str,
    role: UserRole,
) -> tuple[int, str]:
    user = create_user(
        db_session,
        email=email,
        password="StrongPass123!",
        full_name=f"{role.value.title()} User",
        role=role,
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123!"},
    )
    assert login_response.status_code == 200
    return user.id, login_response.json()["access_token"]


def _approve_job(client: TestClient, db_session: Session, job_id: int) -> None:
    _, admin_token = _create_user_and_login(
        client,
        db_session,
        email=f"jobs.admin.{job_id}@example.com",
        role=UserRole.ADMIN,
    )
    response = client.post(
        f"/api/v1/admin/moderation/jobs/{job_id}/approve",
        json={"note": "Approved for tests."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200


def test_recruiter_can_create_job_for_owned_company(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="jobs.owner@example.com",
        role=UserRole.RECRUITER,
    )
    company_response = client.post(
        "/api/v1/companies",
        json={"name": "Jobs Co"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]

    response = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "Backend Engineer",
            "location": "Remote",
            "employment_type": "full-time",
            "description": "Build and maintain APIs.",
        },
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    payload = response.json()

    assert response.status_code == 201
    assert payload["company_id"] == company_id
    assert payload["title"] == "Backend Engineer"
    assert payload["location"] == "Remote"
    assert payload["employment_type"] == "full-time"
    assert payload["tags"] == []
    assert "tag_slugs_list" not in payload


def test_job_create_requires_recruiter_role(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="jobs.recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    _, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="jobs.candidate@example.com",
        role=UserRole.CANDIDATE,
    )
    company_response = client.post(
        "/api/v1/companies",
        json={"name": "Only Recruiters Co"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]

    forbidden_response = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "Forbidden Role",
            "description": "Should not be created by candidate.",
        },
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    unauthenticated_response = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "No Auth Role",
            "description": "Should not be created without token.",
        },
    )

    assert forbidden_response.status_code == 403
    assert forbidden_response.json()["detail"] == "Insufficient permissions."
    assert unauthenticated_response.status_code == 401


def test_recruiter_cannot_create_job_for_unrelated_company(
    client: TestClient,
    db_session: Session,
) -> None:
    _, owner_token = _create_user_and_login(
        client,
        db_session,
        email="company.owner@example.com",
        role=UserRole.RECRUITER,
    )
    _, other_recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="other.recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    company_response = client.post(
        "/api/v1/companies",
        json={"name": "Private Company"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]

    response = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "Unauthorized Job",
            "description": "Should fail for non-member recruiter.",
        },
        headers={"Authorization": f"Bearer {other_recruiter_token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Recruiter has no access to this company."


def test_public_and_candidate_can_list_and_read_job_details(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="jobs.publisher@example.com",
        role=UserRole.RECRUITER,
    )
    _, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="jobs.viewer@example.com",
        role=UserRole.CANDIDATE,
    )
    company_response = client.post(
        "/api/v1/companies",
        json={"name": "Public Jobs Co"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]

    create_job_response = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "Public Backend Engineer",
            "description": "Visible to everyone.",
        },
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert create_job_response.status_code == 201
    job_id = create_job_response.json()["id"]
    _approve_job(client, db_session, job_id)

    public_list_response = client.get("/api/v1/jobs")
    candidate_list_response = client.get(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    public_detail_response = client.get(f"/api/v1/jobs/{job_id}")

    assert public_list_response.status_code == 200
    assert len(public_list_response.json()) == 1
    assert public_list_response.json()[0]["title"] == "Public Backend Engineer"
    job_payload = public_list_response.json()[0]
    assert job_payload["tags"] == []
    assert "tag_slugs_list" not in job_payload
    assert candidate_list_response.status_code == 200
    assert len(candidate_list_response.json()) == 1
    assert candidate_list_response.json()[0]["id"] == job_id
    assert public_detail_response.status_code == 200
    assert public_detail_response.json()["id"] == job_id


def test_recruiter_me_jobs_shows_owner_and_member_scope_only(
    client: TestClient,
    db_session: Session,
) -> None:
    _, owner_token = _create_user_and_login(
        client,
        db_session,
        email="jobs.scope.owner@example.com",
        role=UserRole.RECRUITER,
    )
    member_id, member_token = _create_user_and_login(
        client,
        db_session,
        email="jobs.scope.member@example.com",
        role=UserRole.RECRUITER,
    )
    _, outsider_token = _create_user_and_login(
        client,
        db_session,
        email="jobs.scope.outsider@example.com",
        role=UserRole.RECRUITER,
    )

    owner_company_response = client.post(
        "/api/v1/companies",
        json={"name": "Owner Scope Co"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert owner_company_response.status_code == 201
    owner_company_id = owner_company_response.json()["id"]
    owner_job_response = client.post(
        "/api/v1/jobs",
        json={
            "company_id": owner_company_id,
            "title": "Owner Scope Job",
            "description": "Owned scope visibility",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert owner_job_response.status_code == 201
    owner_job_id = owner_job_response.json()["id"]

    outsider_company_response = client.post(
        "/api/v1/companies",
        json={"name": "Member Scope Co"},
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert outsider_company_response.status_code == 201
    outsider_company_id = outsider_company_response.json()["id"]

    add_member_response = client.post(
        f"/api/v1/companies/{outsider_company_id}/recruiters",
        json={"recruiter_user_id": member_id},
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert add_member_response.status_code == 201
    membership_job_response = client.post(
        "/api/v1/jobs",
        json={
            "company_id": outsider_company_id,
            "title": "Member Scope Job",
            "description": "Membership scope visibility",
        },
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert membership_job_response.status_code == 201
    membership_job_id = membership_job_response.json()["id"]

    owner_scope_response = client.get(
        "/api/v1/jobs/me",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    member_scope_response = client.get(
        "/api/v1/jobs/me",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    outsider_scope_response = client.get(
        "/api/v1/jobs/me",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )

    assert owner_scope_response.status_code == 200
    assert [job["id"] for job in owner_scope_response.json()] == [owner_job_id]
    assert member_scope_response.status_code == 200
    assert [job["id"] for job in member_scope_response.json()] == [membership_job_id]
    assert outsider_scope_response.status_code == 200
    assert [job["id"] for job in outsider_scope_response.json()] == [membership_job_id]


def test_jobs_endpoint_supports_filters_and_pagination(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="jobs.filter.owner@example.com",
        role=UserRole.RECRUITER,
    )
    company_response = client.post(
        "/api/v1/companies",
        json={"name": "Filter Co"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]

    first_job = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "Backend Python Engineer",
            "location": "Remote",
            "employment_type": "full-time",
            "description": "First filtered job",
        },
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    second_job = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "Frontend React Engineer",
            "location": "Krakow",
            "employment_type": "contract",
            "description": "Second filtered job",
        },
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert first_job.status_code == 201
    assert second_job.status_code == 201
    first_job_id = first_job.json()["id"]
    second_job_id = second_job.json()["id"]
    _approve_job(client, db_session, first_job_id)
    _approve_job(client, db_session, second_job_id)

    title_filtered = client.get("/api/v1/jobs?title_query=Python")
    location_filtered = client.get("/api/v1/jobs?location=Krakow")
    type_filtered = client.get("/api/v1/jobs?employment_type=full-time")
    company_filtered = client.get(f"/api/v1/jobs?company_id={company_id}")
    paginated = client.get("/api/v1/jobs?page=1&page_size=1")

    assert title_filtered.status_code == 200
    assert [job["id"] for job in title_filtered.json()] == [first_job_id]
    assert location_filtered.status_code == 200
    assert [job["id"] for job in location_filtered.json()] == [second_job_id]
    assert type_filtered.status_code == 200
    assert [job["id"] for job in type_filtered.json()] == [first_job_id]
    assert company_filtered.status_code == 200
    assert len(company_filtered.json()) == 2
    assert paginated.status_code == 200
    assert len(paginated.json()) == 1


def test_pending_job_not_listed_publicly_and_detail_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="jobs.pending.pub@example.com",
        role=UserRole.RECRUITER,
    )
    company_response = client.post(
        "/api/v1/companies",
        json={"name": "Pending Pub Co"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]
    job_response = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "Awaiting moderation",
            "description": "Not visible publicly yet.",
        },
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert job_response.status_code == 201
    job_id = job_response.json()["id"]

    list_resp = client.get("/api/v1/jobs")
    detail_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert list_resp.status_code == 200
    assert list_resp.json() == []
    assert detail_resp.status_code == 404


def test_public_jobs_can_filter_by_tags_and_pending_jobs_are_excluded(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="jobs.tags.owner@example.com",
        role=UserRole.RECRUITER,
    )
    company_response = client.post(
        "/api/v1/companies",
        json={"name": "Tagged Jobs Co"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]

    job_a = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "Staff Engineer",
            "description": "Senior backend.",
            "tags": ["python", "backend"],
        },
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    job_b = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "Rust Engineer",
            "description": "Systems.",
            "tags": ["rust"],
        },
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    pending = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "Draft Role",
            "description": "Still pending moderation.",
            "tags": ["python"],
        },
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert job_a.status_code == 201
    assert job_b.status_code == 201
    assert pending.status_code == 201
    job_a_id = job_a.json()["id"]
    job_b_id = job_b.json()["id"]
    _approve_job(client, db_session, job_a_id)
    _approve_job(client, db_session, job_b_id)

    python_backend = client.get("/api/v1/jobs", params=[("tag", "python"), ("tag", "backend")])
    rust_only = client.get("/api/v1/jobs", params=[("tag", "rust")])
    python_any = client.get("/api/v1/jobs", params=[("tag", "python")])

    assert python_backend.status_code == 200
    pb_rows = python_backend.json()
    assert [j["id"] for j in pb_rows] == [job_a_id]
    assert pb_rows[0]["tags"] == ["backend", "python"]
    assert "tag_slugs_list" not in pb_rows[0]
    assert rust_only.status_code == 200
    assert [j["id"] for j in rust_only.json()] == [job_b_id]
    assert python_any.status_code == 200
    assert [j["id"] for j in python_any.json()] == [job_a_id]


def test_public_jobs_tag_filter_rejects_more_than_max_tags(client: TestClient) -> None:
    params = [("tag", f"t{i}") for i in range(25)]
    response = client.get("/api/v1/jobs", params=params)

    assert response.status_code == 422


def test_job_detail_returns_404_for_missing_job(client: TestClient) -> None:
    response = client.get("/api/v1/jobs/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found."


def test_recruiter_put_job_resets_moderation_and_replaces_tags(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="jobs.put.owner@example.com",
        role=UserRole.RECRUITER,
    )
    company_response = client.post(
        "/api/v1/companies",
        json={"name": "Put Jobs Co"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]
    create_resp = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "Original Title",
            "description": "Original desc.",
            "tags": ["python"],
        },
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]
    _approve_job(client, db_session, job_id)

    detail_before = client.get(f"/api/v1/jobs/{job_id}")
    assert detail_before.status_code == 200

    put_resp = client.put(
        f"/api/v1/jobs/{job_id}",
        json={
            "title": "Replaced Title",
            "location": "Berlin",
            "employment_type": "contract",
            "description": "Updated description.",
            "tags": ["django", "python"],
        },
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert put_resp.status_code == 200
    body = put_resp.json()
    assert body["title"] == "Replaced Title"
    assert body["location"] == "Berlin"
    assert body["employment_type"] == "contract"
    assert body["moderation_status"] == "pending"
    assert body["tags"] == ["django", "python"]

    assert client.get(f"/api/v1/jobs/{job_id}").status_code == 404


def test_recruiter_patch_job_updates_fields_and_tags(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="jobs.patch.owner@example.com",
        role=UserRole.RECRUITER,
    )
    company_response = client.post(
        "/api/v1/companies",
        json={"name": "Patch Jobs Co"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]
    create_resp = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "Patchable",
            "description": "Desc.",
            "tags": ["java"],
        },
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]

    patch_resp = client.patch(
        f"/api/v1/jobs/{job_id}",
        json={"title": "Patched Title", "tags": ["kotlin"]},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert patch_resp.status_code == 200
    body = patch_resp.json()
    assert body["title"] == "Patched Title"
    assert body["tags"] == ["kotlin"]
    assert body["moderation_status"] == "pending"


def test_recruiter_can_delete_own_job_and_detail_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="jobs.del.owner@example.com",
        role=UserRole.RECRUITER,
    )
    company_response = client.post(
        "/api/v1/companies",
        json={"name": "Del Jobs Co"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]
    create_resp = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "To Delete",
            "description": "Bye.",
        },
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]
    _approve_job(client, db_session, job_id)

    assert client.get(f"/api/v1/jobs/{job_id}").status_code == 200

    delete_resp = client.delete(
        f"/api/v1/jobs/{job_id}",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert delete_resp.status_code == 204

    assert client.get(f"/api/v1/jobs/{job_id}").status_code == 404


def test_other_recruiter_cannot_put_patch_delete_job(
    client: TestClient,
    db_session: Session,
) -> None:
    _, owner_token = _create_user_and_login(
        client,
        db_session,
        email="jobs.crud.owner@example.com",
        role=UserRole.RECRUITER,
    )
    _, outsider_token = _create_user_and_login(
        client,
        db_session,
        email="jobs.crud.outsider@example.com",
        role=UserRole.RECRUITER,
    )
    company_response = client.post(
        "/api/v1/companies",
        json={"name": "Crud Jobs Co"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]
    create_resp = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "Protected Job",
            "description": "Private listing.",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]

    replace_body = {
        "title": "Nope",
        "description": "Should fail.",
        "tags": [],
    }
    put_resp = client.put(
        f"/api/v1/jobs/{job_id}",
        json=replace_body,
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    patch_resp = client.patch(
        f"/api/v1/jobs/{job_id}",
        json={"title": "Also nope"},
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    delete_resp = client.delete(
        f"/api/v1/jobs/{job_id}",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )

    assert put_resp.status_code == 403
    assert patch_resp.status_code == 403
    assert delete_resp.status_code == 403
