import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
def test_docs_view_default_render() -> None:
    client = Client()
    url = reverse("docs")
    response = client.get(url)

    assert response.status_code == 200
    assert "ui/docs.html" in [t.name for t in response.templates if t.name]
    content = response.content.decode("utf-8")
    assert "EXPLORER: SPOTTER-DOCS" in content
    assert "Clean Architecture and Domain Isolation" in content
    assert "vscode-sidebar" in content
    assert "vscode-editor" in content


@pytest.mark.django_db
def test_docs_view_specific_document() -> None:
    client = Client()
    url = reverse("docs")
    target_slug = "05-learning-journey/first-time-with-postgis-and-spatial-sql"
    response = client.get(url, {"doc": target_slug})

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "First Time with PostGIS and Spatial SQL" in content
    assert "ST_LineLocatePoint" in content


@pytest.mark.django_db
def test_docs_view_json_format() -> None:
    client = Client()
    url = reverse("docs")
    target_slug = "02-current-system/greedy-lookahead-refueling-engine"
    response = client.get(url, {"doc": target_slug, "format": "json"})

    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == target_slug
    assert data["title"] == "Greedy Lookahead Refueling Engine"
    assert "500 miles" in data["html_content"]
    assert data["reading_time_minutes"] >= 1
    assert "previous_doc" in data
    assert "next_doc" in data


@pytest.mark.django_db
def test_docs_view_invalid_slug_fallback() -> None:
    client = Client()
    url = reverse("docs")
    response = client.get(url, {"doc": "completely-invalid-slug"})

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Clean Architecture and Domain Isolation" in content


@pytest.mark.django_db
def test_navigation_bar_contains_docs_between_dataset_and_theme() -> None:
    client = Client()
    url = reverse("home")
    response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    # Verify exact ordering: Add Dataset -> Docs -> theme-toggle
    dataset_pos = content.find('href="/datasets/"')
    docs_pos = content.find('href="/docs/"')
    theme_pos = content.find('id="theme-toggle"')

    assert dataset_pos != -1, "Add Dataset link not found in navbar"
    assert docs_pos != -1, "Docs link not found in navbar"
    assert theme_pos != -1, "Theme toggle not found in navbar"
    assert dataset_pos < docs_pos < theme_pos, (
        f"Docs link must be between Add Dataset and theme-toggle. "
        f"dataset={dataset_pos}, docs={docs_pos}, theme={theme_pos}"
    )


@pytest.mark.django_db
def test_docs_nav_link_active_state() -> None:
    client = Client()
    url = reverse("docs")
    response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert 'href="/docs/" class="active"' in content
