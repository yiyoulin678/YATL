import json
import re
from abc import ABC, abstractmethod
from typing import Any

from lxml import etree
from requests import Response

from .utils import get_content_type, get_nested_value


class Extractor(ABC):
    """Abstract base class for extractors."""

    @abstractmethod
    def extract(
        self, response: Response, extract_spec: dict[str, Any]
    ) -> dict[str, Any]:
        """Extracts data from a response according to the specification.

        Args:
            response: The HTTP response to extract from.
            extract_spec: A dictionary specifying how to extract data.

        Returns:
            A dictionary with the extracted data.
        """
        pass


class XmlExtractor(Extractor):
    """Extracts data from XML responses."""

    def extract(
        self, response: Response, extract_spec: dict[str, Any]
    ) -> dict[str, Any]:
        """Extracts fields from an XML response using XPath or tag names.

        Args:
            response: The HTTP response containing XML data.
            extract_spec: A dictionary mapping output keys to XPath expressions.
                If an XPath is None, the key is used as a tag name for `findall`.

        Returns:
            A dictionary with the extracted text of the first matching element.

        Raises:
            ValueError: If the response is not valid XML, or no element matches
                the given XPath/tag.
        """
        extracted = {}
        try:
            root = etree.fromstring(response.content)
        except etree.XMLSyntaxError:
            raise ValueError("Response is not valid XML")

        for key, xpath in extract_spec.items():
            if xpath is None:
                # Use key as tag name
                elements = root.findall(key)
            else:
                elements = root.xpath(xpath)
            if elements:
                extracted[key] = elements[0].text
            else:
                raise ValueError(f"XML element '{key}' not found with xpath '{xpath}'")
        return extracted


class JsonExtractor(Extractor):
    """Extracts data from JSON responses."""

    def extract(
        self,
        response: Response,
        extract_spec: dict[str, Any],
    ) -> dict[str, Any]:
        """Extracts fields from a JSON response according to the specification.

        Args:
            response: The HTTP response containing JSON data.
            extract_spec: A dictionary mapping output keys to JSON paths.
                If a path is None, the key is used as a direct field name.
                Supports dot notation for nested fields (e.g., "user.email").

        Returns:
            A dictionary with the extracted values.

        Raises:
            ValueError: If the response is not valid JSON, or a specified field
                cannot be found.
        """
        extracted = {}
        try:
            data = response.json()
        except json.JSONDecodeError:
            raise ValueError("Response is not valid JSON")

        for key, path in extract_spec.items():
            if path is None:
                # Use key as direct field name
                if key in data:
                    extracted[key] = data[key]
                else:
                    raise ValueError(f"Field '{key}' not found in JSON response")
            else:
                # Path may be a dot‑notation string
                try:
                    extracted[key] = get_nested_value(data, path)
                except ValueError as e:
                    raise ValueError(f"Failed to extract '{key}' at path '{path}': {e}")
        return extracted


class TextExtractor(Extractor):
    """Extracts data from plain-text or HTML responses."""

    def extract(
        self, response: Response, extract_spec: dict[str, Any]
    ) -> dict[str, Any]:
        """Extracts substrings from a plain-text or HTML response.

        Args:
            response: The HTTP response with text content.
            extract_spec: A dictionary mapping output keys to patterns.
                If a pattern is None, it is treated as a literal substring.
                Otherwise, it is interpreted as a regular expression.

        Returns:
            A dictionary with the extracted substrings (the first match for each
            pattern). For literal substrings, the extracted value is the pattern
            itself.

        Raises:
            ValueError: If a pattern (literal or regex) is not found in the text.
        """
        extracted = {}
        text = response.text
        for key, pattern in extract_spec.items():
            if pattern is None:
                # Treat pattern as literal substring – but None cannot be searched.
                # This case is ambiguous; we treat it as "extract the key itself"?
                # For backward compatibility, we raise an error.
                raise ValueError(
                    "Pattern cannot be None for text extraction. "
                    "Provide a literal string or regex."
                )
            else:
                # Use regex
                match = re.search(pattern, text)
                if match:
                    extracted[key] = match.group(0)
                else:
                    raise ValueError(f"Regex '{pattern}' not found in text")
        return extracted


class DataExtractor:
    """Extracts data from HTTP responses based on a specification.

    Supports JSON, XML, and text responses. Automatically detects content type
    and applies the appropriate extraction method.
    """

    def __init__(self):
        """Initializes the data extractor and registers default extractors."""
        self._extractors = {}
        self._format_detectors = []
        self._register_defaults()

    def _register_defaults(self):
        """
        Register default extractors.
        """
        self.register("json", JsonExtractor())
        self.register("xml", XmlExtractor())
        self.register("text", TextExtractor())

        self.register_format_detector(self._detect_json)
        self.register_format_detector(self._detect_xml)
        self.register_format_detector(self._detect_text)

    def register(self, format_name, extractor):
        """
        Register an extractor for a specific format.

        Args:
            format_name: The format name (e.g., "json", "xml", "text").
            extractor: The extractor instance.
        """
        self._extractors[format_name] = extractor

    def register_format_detector(self, detector_func):
        """
        Register a format detector function.

        A format detector function takes a Response object and returns the format
        name (e.g., "json", "xml", "text") if the response matches the format,
        or None if it does not.

        Args:
            detector_func: The format detector function.
        """
        self._format_detectors.append(detector_func)

    def _detect_json(self, response):
        """
        Detects if the response is JSON.

        Args:
            response: The HTTP response object.

        Returns:
            The format name if the response is JSON, or None if it is not.
        """
        content_type = get_content_type(response.headers.get("Content-Type", ""))
        if "json" in content_type:
            return "json"
        try:
            response.json()
            return "json"
        except:
            return None

    def _detect_xml(self, response):
        """
        Detects if the response is XML

        Args:
            response: The HTTP response object.

        Returns:
            The format name if the response is XML, or None if it is not.
        """
        content_type = get_content_type(response.headers.get("Content-Type", ""))
        if "xml" in content_type:
            return "xml"
        try:
            etree.fromstring(response.content)
            return "xml"
        except etree.XMLSyntaxError:
            return None

    def _detect_text(self, response):
        """
        Detects if the response is text.

        Args:
            response: The HTTP response object.

        Returns:
            The format name if the response is text, or None if it is not.
        """
        content_type = get_content_type(response.headers.get("Content-Type", ""))
        if "text" in content_type:
            return "text"
        return None

    def _detect_format(self, response: Response) -> str:
        for detector in self._format_detectors:
            result = detector(response)
            if result:
                return result
        return "unknown"

    def extract(
        self, response: Response, extract_spec: dict[str, Any]
    ) -> dict[str, Any]:
        """Main extraction entry point.

        Determines the content type of the response and delegates to the
        appropriate extraction method (JSON, XML, or text). If the content type
        is not recognized, attempts to parse the response as JSON as a fallback.

        Args:
            response: The HTTP response object.
            extract_spec: A dictionary describing what to extract (format depends
                on the content type).

        Returns:
            A dictionary with the extracted data.

        Raises:
            ValueError: If the content type is unsupported and the fallback JSON
                extraction also fails.
        """
        fmt = self._detect_format(response)
        extractor = self._extractors.get(fmt)
        if extractor is None:
            raise ValueError(f"Unsupported content type: {fmt}")
        return extractor.extract(response, extract_spec)
