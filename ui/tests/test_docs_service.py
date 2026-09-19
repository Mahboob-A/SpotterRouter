from ui.docs_service import DocsService


def test_docs_service_catalog_loaded() -> None:
    service = DocsService()
    categories = service.get_categories()
    assert len(categories) == 6

    flat_docs = service.get_flat_docs()
    assert len(flat_docs) == 17

    category_ids = [c.id for c in categories]
    assert category_ids == [
        "01-architecture",
        "02-current-system",
        "03-tradeoffs",
        "04-brainstorming-and-failed-paths",
        "05-learning-journey",
        "06-preparation-and-testing",
    ]


def test_docs_service_all_files_exist_and_render() -> None:
    service = DocsService()
    flat_docs = service.get_flat_docs()

    for doc_meta in flat_docs:
        detail = service.get_doc_detail(doc_meta.slug)
        assert detail is not None
        assert detail.metadata.title == doc_meta.title
        assert len(detail.html_content) > 100
        assert "<h" in detail.html_content
        assert detail.metadata.reading_time_minutes >= 1


def test_docs_service_navigation_chain() -> None:
    service = DocsService()
    first_slug = service.get_default_slug()
    first_detail = service.get_doc_detail(first_slug)
    assert first_detail is not None
    assert first_detail.previous_doc is None
    assert first_detail.next_doc is not None

    last_doc = service.get_flat_docs()[-1]
    last_detail = service.get_doc_detail(last_doc.slug)
    assert last_detail is not None
    assert last_detail.next_doc is None
    assert last_detail.previous_doc is not None


def test_docs_service_search() -> None:
    service = DocsService()
    postgis_results = service.search_docs("postgis")
    assert len(postgis_results) >= 2

    empty_results = service.search_docs("nonexistent_term_xyz")
    assert len(empty_results) == 0
