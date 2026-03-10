"""TDD tests for embeddings/text_builder.py."""


from talent_graph.embeddings.text_builder import build_person_text, build_query_text


class TestBuildPersonText:
    def test_minimal_person(self):
        """Only name provided — returns just the name."""
        text = build_person_text(name="Alice")
        assert text == "Alice"

    def test_with_org(self):
        text = build_person_text(name="Alice", org_name="MIT")
        assert "Alice" in text
        assert "MIT" in text

    def test_with_concepts(self):
        text = build_person_text(name="Alice", concepts=["machine learning", "NLP"])
        assert "machine learning" in text
        assert "NLP" in text

    def test_with_paper_titles(self):
        text = build_person_text(name="Alice", paper_titles=["Attention Is All You Need"])
        assert "Attention Is All You Need" in text

    def test_full_person(self):
        text = build_person_text(
            name="Bob",
            org_name="Stanford",
            concepts=["deep learning", "computer vision"],
            paper_titles=["ResNet", "ImageNet Classification"],
        )
        assert "Bob" in text
        assert "Stanford" in text
        assert "deep learning" in text
        assert "computer vision" in text
        assert "ResNet" in text
        assert "ImageNet Classification" in text

    def test_none_values_are_skipped(self):
        """None org_name must not produce 'None' in output."""
        text = build_person_text(name="Alice", org_name=None)
        assert "None" not in text

    def test_empty_lists_produce_no_noise(self):
        text = build_person_text(name="Alice", concepts=[], paper_titles=[])
        assert text.strip() == "Alice"

    def test_returns_string(self):
        result = build_person_text(name="Alice")
        assert isinstance(result, str)

    def test_deduplicates_paper_titles(self):
        text = build_person_text(
            name="Alice",
            paper_titles=["ResNet", "ResNet", "AlexNet"],
        )
        # "ResNet" should appear only once
        assert text.count("ResNet") == 1

    def test_truncates_long_paper_list(self):
        """Caps paper titles at 10 to keep embedding text focused."""
        titles = [f"Paper {i}" for i in range(20)]
        text = build_person_text(name="Alice", paper_titles=titles)
        # Only first 10 papers included
        for i in range(10):
            assert f"Paper {i}" in text
        for i in range(10, 20):
            assert f"Paper {i}" not in text


class TestBuildQueryText:
    def test_simple_query(self):
        text = build_query_text("attention mechanism transformers")
        assert text == "attention mechanism transformers"

    def test_strips_whitespace(self):
        text = build_query_text("  neural networks  ")
        assert text == "neural networks"

    def test_returns_string(self):
        assert isinstance(build_query_text("foo"), str)
