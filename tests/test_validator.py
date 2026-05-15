import json

import pytest
from requests import Response

from src.yatl.validator import validate_json_body, validate_xml_body


class MockJsonResponse(Response):
    """Mock response with configurable JSON content."""

    def __init__(self, json_data, status_code=200):
        super().__init__()
        self._json_data = json_data
        self.status_code = status_code
        self.headers["Content-Type"] = "application/json"

    def json(self):
        return self._json_data


class MockXmlResponse(Response):
    """Mock response with configurable XML content."""

    def __init__(self, xml_data, status_code=200):
        super().__init__()
        self._content = xml_data.encode("utf-8")
        self.status_code = status_code
        self.headers["Content-Type"] = "application/xml"

    @property
    def content(self):
        return self._content


def test_validate_xml_body_simple():
    """Simple test for XML validation."""
    xml = """<?xml version="1.0"?>
    <message>
        <from>YATL</from>
        <to>API Server</to>
        <content>Hello World</content>
    </message>"""

    response = MockXmlResponse(xml)
    validate_xml_body(
        response,
        {
            "/message/from": "YATL",
            "/message/to": "API Server",
            "/message/content": "Hello World",
        },
    )


def test_nested_xml_body_validation():
    """Test nested XML validation."""
    xml = """<?xml version="1.0"?>
    <message>
        <from>YATL</from>
        <to>API Server</to>
        <content>
            <text>Hello World</text>
            <date>2022-01-01</date>
        </content>
    </message>"""

    response = MockXmlResponse(xml)
    validate_xml_body(
        response,
        {
            "/message/from": "YATL",
            "/message/to": "API Server",
            "/message/content/text": "Hello World",
            "/message/content/date": "2022-01-01",
        },
    )


def test_validate_xml_body_with_indexed_xpath():
    nested_xml = """<?xml version="1.0" encoding="UTF-8"?>
                <company>
                    <name>TechCorp</name>
                    <departments>
                        <department id="1">
                            <name>Engineering</name>
                            <employees>
                                <employee>
                                    <id>101</id>
                                    <name>John Doe</name>
                                    <position>Senior Developer</position>
                                    <skills>
                                        <skill>Python</skill>
                                        <skill>FastAPI</skill>
                                        <skill>XML</skill>
                                    </skills>
                                </employee>
                                <employee>
                                    <id>102</id>
                                    <name>Jane Smith</name>
                                    <position>QA Engineer</position>
                                    <skills>
                                        <skill>Testing</skill>
                                        <skill>Automation</skill>
                                    </skills>
                                </employee>
                            </employees>
                        </department>
                        <department id="2">
                            <name>Sales</name>
                            <employees>
                                <employee>
                                    <id>201</id>
                                    <name>Bob Johnson</name>
                                    <position>Sales Manager</position>
                                </employee>
                            </employees>
                        </department>
                    </departments>
                </company>"""

    response = MockXmlResponse(nested_xml)
    validate_xml_body(
        response,
        {
            "/company/name": "TechCorp",
            "/company/departments/department[1]/name": "Engineering",
            "/company/departments/department[1]/employees/employee[1]/name": "John Doe",
            "/company/departments/department[1]/employees/employee[1]/position": "Senior Developer",
            "/company/departments/department[1]/employees/employee[1]/skills/skill[1]": "Python",
            "/company/departments/department[1]/employees/employee[1]/skills/skill[2]": "FastAPI",
            "/company/departments/department[2]/name": "Sales",
            "/company/departments/department[2]/employees/employee[1]/id": "201",
        },
    )


def test_validate_xml_body_invalid_xml():
    response = MockXmlResponse("not xml at all")
    with pytest.raises(AssertionError, match="Response is not valid XML"):
        validate_xml_body(response, {})


def test_validate_xml_body_missing_element():
    xml = "<message><from>YATL</from></message>"
    response = MockXmlResponse(xml)
    with pytest.raises(
        AssertionError, match="XML element with xpath '/message/to' not found"
    ):
        validate_xml_body(response, {"/message/to": "API Server"})


def test_validate_xml_body_value_mismatch():
    xml = "<message><from>YATL</from></message>"
    response = MockXmlResponse(xml)
    with pytest.raises(
        AssertionError,
        match="XML element '/message/from' expected 'Different', got 'YATL'",
    ):
        validate_xml_body(response, {"/message/from": "Different"})


def test_validate_json_body_simple():
    """Test simple flat JSON validation."""
    response = MockJsonResponse({"name": "Alice", "age": 30})
    validate_json_body(response, {"name": "Alice", "age": 30})


def test_validate_json_body_nested():
    """Test nested object validation."""
    response = MockJsonResponse(
        {
            "user": {"name": "Bob", "address": {"city": "Moscow", "zip": "123456"}},
            "active": True,
        }
    )
    validate_json_body(
        response,
        {
            "user": {"name": "Bob", "address": {"city": "Moscow", "zip": "123456"}},
            "active": True,
        },
    )


def test_validate_json_body_dot_notation():
    """Test dot-notation for deeply nested fields."""
    response = MockJsonResponse(
        {"a": {"b": {"c": 42}}, "items": [{"id": 1}, {"id": 2}]}
    )
    validate_json_body(response, {"a.b.c": 42, "items.0.id": 1})


def test_validate_json_body_different_types():
    """Test validation of various data types."""
    response = MockJsonResponse(
        {
            "string": "hello",
            "number": 123,
            "float": 45.67,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3],
            "empty_object": {},
        }
    )
    validate_json_body(
        response,
        {
            "string": "hello",
            "number": 123,
            "float": 45.67,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3],
            "empty_object": {},
        },
    )


def test_validate_json_body_empty():
    """Test empty object validation."""
    response = MockJsonResponse({})
    validate_json_body(response, {})


def test_validate_json_body_invalid_json():
    """Test when response is not valid JSON."""

    class InvalidJSONResponse(Response):
        def __init__(self):
            super().__init__()
            self.headers["Content-Type"] = "application/json"

        def json(self):
            raise json.JSONDecodeError("Expecting value", "", 0)

    response = InvalidJSONResponse()
    with pytest.raises(AssertionError, match="Response is not valid JSON"):
        validate_json_body(response, {})


def test_validate_json_body_missing_key():
    """Test missing key in response."""
    response = MockJsonResponse({"name": "Alice"})
    with pytest.raises(AssertionError, match="Key 'age' is missing in response"):
        validate_json_body(response, {"name": "Alice", "age": 30})


def test_validate_json_body_value_mismatch():
    """Test value mismatch."""
    response = MockJsonResponse({"name": "Alice", "age": 30})
    with pytest.raises(AssertionError, match="For key 'age' expected '31', got '30'"):
        validate_json_body(response, {"name": "Alice", "age": 31})


def test_validate_json_body_nested_mismatch():
    """Test mismatch in nested object."""
    response = MockJsonResponse(
        {"user": {"name": "Bob", "address": {"city": "Moscow", "zip": "123456"}}}
    )
    with pytest.raises(
        AssertionError, match="For key 'city' expected 'SPb', got 'Moscow'"
    ):
        validate_json_body(
            response,
            {"user": {"name": "Bob", "address": {"city": "SPb", "zip": "123456"}}},
        )


def test_validate_json_body_dot_notation_not_found():
    """Test when dot-notation path is not found."""
    response = MockJsonResponse({"a": {"b": {"c": 42}}})
    with pytest.raises(AssertionError, match="Path 'a.b.d' not found in response"):
        validate_json_body(response, {"a.b.d": 42})


def test_validate_json_body_dot_notation_mismatch():
    """Test dot-notation value mismatch."""
    response = MockJsonResponse({"a": {"b": {"c": 42}}})
    with pytest.raises(
        AssertionError, match="For path 'a.b.c' expected '43', got '42'"
    ):
        validate_json_body(response, {"a.b.c": 43})


def test_validate_json_body_type_mismatch():
    """Test type mismatch (string vs number)."""
    response = MockJsonResponse({"count": "123"})
    with pytest.raises(
        AssertionError, match="For key 'count' expected '123', got '123'"
    ):
        validate_json_body(response, {"count": 123})
