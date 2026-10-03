import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Multi-Agent Instagram Growth Brain" in data["message"]

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["pass_threshold_10"] == 8.5
    assert data["max_rewrites"] == 3

def test_memory_top_posts():
    response = client.get("/api/memory/top-posts?limit=3")
    assert response.status_code == 200
    posts = response.json()
    assert len(posts) <= 3
    assert all("post_id" in p for p in posts)

def test_memory_fatigued_and_marking():
    # Mark a topic fatigued
    post_res = client.post("/api/memory/fatigue?topic=Prelims%20Timer&reason=Overused")
    assert post_res.status_code == 200
    
    # Retrieve fatigued list
    get_res = client.get("/api/memory/fatigued")
    assert get_res.status_code == 200
    fatigued = get_res.json()
    assert "Prelims Timer" in fatigued

def test_feedback_logging():
    payload = {
        "script_id": "test_script_42",
        "engagement_rate": 7.8,
        "views": 150000,
        "saves": 12000,
        "shares": 5000,
        "comments": 400,
    }
    res = client.post("/api/feedback", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "success"
