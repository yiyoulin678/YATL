def test_render_template(template_render):
    "Test that render_template returns a rendered template."
    data = {
        "user": "{{ name }}",
        "items": ["{{id}}", "static"],
        "nested": {"key": "{{ value }}"},
    }
    context = {"name": "Alice", "id": 42, "value": "secret"}
    result = template_render.render_data(data, context)
    assert result == {
        "user": "Alice",
        "items": ["42", "static"],
        "nested": {"key": "secret"},
    }


def test_render_preserves_non_string_scalar_values(template_render):
    "Test that non-string values are returned unchanged."
    data = {
        "count": 3,
        "enabled": True,
        "missing": None,
        "ratio": 0.75,
    }

    result = template_render.render_data(data, {"count": 10})

    assert result == data


def test_render_template_in_deeply_nested_lists(template_render):
    "Test that templates nested in lists and dictionaries are rendered."
    data = {
        "payload": [
            {"name": "{{ user.name }}"},
            ["{{ user.id }}", {"role": "{{ role }}"}],
        ]
    }
    context = {"user": {"name": "Alice", "id": 42}, "role": "admin"}

    result = template_render.render_data(data, context)

    assert result == {
        "payload": [
            {"name": "Alice"},
            ["42", {"role": "admin"}],
        ]
    }


def test_render_preserves_dictionary_keys(template_render):
    "Test that dictionary keys are not treated as templates."
    data = {"{{ dynamic_key }}": "{{ value }}"}

    result = template_render.render_data(
        data, {"dynamic_key": "name", "value": "Alice"}
    )

    assert result == {"{{ dynamic_key }}": "Alice"}


def test_render_reuses_cached_templates(template_render):
    "Test that rendering duplicate template strings reuses one compiled template."
    data = ["{{ item }}", "{{ item }}", {"nested": "{{ item }}"}]

    result = template_render.render_data(data, {"item": "book"})

    assert result == ["book", "book", {"nested": "book"}]
    assert len(template_render._template_cache) == 1
