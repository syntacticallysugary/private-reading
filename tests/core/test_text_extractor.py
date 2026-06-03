"""Tests for TextExtractor class."""

import pytest
from pathlib import Path
import tempfile
import os

from private_reading.exceptions import TextExtractionError, UnsupportedFormatError
from private_reading.core.text_extractor import TextExtractor


class TestTextExtractor:
    """Test cases for TextExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create TextExtractor instance."""
        return TextExtractor()

    @pytest.fixture
    def sample_markdown(self):
        """Sample markdown content for testing."""
        return """# Sample Document

This is a **bold** statement and this is *italic* text.

## Section 1

This is a code block:

```python
def hello():
    print("Hello, World!")
```

## Section 2

This is a regular paragraph with some more content.

- List item 1
- List item 2

[Link text](https://example.com)
---
"""

    @pytest.fixture
    def sample_txt(self):
        """Sample plain text content."""
        return """This is a sample paragraph for testing purposes. It contains multiple sentences that should be split into chunks.

The second paragraph continues the text with additional content for semantic chunking. This helps verify that the chunking algorithm works correctly.
"""

    @pytest.mark.asyncio
    async def test_extract_markdown(self, extractor, tmp_dir, sample_markdown):
        """Test markdown text extraction strips formatting."""
        file_path = tmp_dir / "test.md"
        file_path.write_text(sample_markdown, encoding="utf-8")

        result = await extractor.extract(file_path)

        # Verify markdown formatting is stripped
        assert "bold" not in result.lower()
        assert "italic" not in result.lower()
        assert "```" not in result
        assert "# Sample Document" not in result
        assert "- List item" not in result
        assert "[Link text]" not in result
        assert "[https://example.com]" not in result
        assert "---" not in result

    @pytest.mark.asyncio
    async def test_extract_pdf(self, extractor, tmp_dir, sample_pdf_file):
        """Test PDF text extraction."""
        # Create a minimal PDF for testing
        import subprocess
        pdf_path = tmp_dir / "sample.pdf"
        
        # Create a simple PDF using pdftk or similar
        # For testing, we'll create a minimal valid PDF
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
72 720 Td
(Hello World) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000057 00000 n
0000000115 00000 n
0000000192 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
315
%%EOF"""
        
        with open(pdf_path, "wb") as f:
            f.write(pdf_content)

        result = await extractor.extract(pdf_path)

        # Verify PDF text was extracted
        assert "Hello World" in result

    @pytest.mark.asyncio
    async def test_extract_txt(self, extractor, tmp_dir, sample_txt):
        """Test plain text extraction."""
        file_path = tmp_dir / "test.txt"
        file_path.write_text(sample_txt, encoding="utf-8")

        result = await extractor.extract(file_path)

        # Verify text was extracted
        assert "sample paragraph" in result.lower()
        assert "semantic chunking" in result.lower()

    @pytest.mark.asyncio
    async def test_extract_txt_legacy_encoding(self, extractor, tmp_dir):
        """Test UTF-8 and legacy encoding fallback."""
        # Create a file with latin-1 encoding
        file_path = tmp_dir / "test.txt"
        latin1_content = "Café résumé naïve".encode("latin-1")
        file_path.write_bytes(latin1_content)

        result = await extractor.extract(file_path)

        # Verify legacy encoding fallback worked
        assert "Café" in result
        assert "résumé" in result

    @pytest.mark.asyncio
    async def test_extract_docx(self, extractor, tmp_dir, sample_docx_file):
        """Test DOCX text extraction."""
        docx_path = sample_docx_file()

        result = await extractor.extract(docx_path)

        # Verify DOCX text was extracted
        assert "sample word document paragraph" in result.lower()
        assert "another paragraph" in result.lower()

    @pytest.mark.asyncio
    async def test_unsupported_format(self, extractor, tmp_dir):
        """Test handling of unsupported file formats."""
        file_path = tmp_dir / "test.xyz"
        file_path.write_text("test content", encoding="utf-8")

        with pytest.raises(UnsupportedFormatError) as exc_info:
            await extractor.extract(file_path)

        assert "Unsupported format" in str(exc_info.value)
        assert ".xyz" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_empty_file(self, extractor, tmp_dir):
        """Test extraction from empty file."""
        file_path = tmp_dir / "empty.txt"
        file_path.write_text("", encoding="utf-8")

        result = await extractor.extract(file_path)

        assert result == "" or result == "\n"

    @pytest.mark.asyncio
    async def test_extract_markdown_code_blocks(self, extractor, tmp_dir):
        """Test markdown code block stripping."""
        content = """# Header

```python
def hello():
    print("Hello")
```

More text.
"""
        file_path = tmp_dir / "test.md"
        file_path.write_text(content, encoding="utf-8")

        result = await extractor.extract(file_path)

        # Verify code block markers are removed
        assert "```" not in result
        assert "def hello" in result  # Code content should remain

    @pytest.mark.asyncio
    async def test_extract_markdown_inline_code(self, extractor, tmp_dir):
        """Test markdown inline code stripping."""
        content = """Text with `inline code` and more text.
"""
        file_path = tmp_dir / "test.md"
        file_path.write_text(content, encoding="utf-8")

        result = await extractor.extract(file_path)

        # Verify inline code markers are removed
        assert "`" not in result
        assert "inline code" in result

    @pytest.mark.asyncio
    async def test_extract_markdown_headers(self, extractor, tmp_dir):
        """Test markdown header stripping."""
        content = """# H1
## H2
### H3
#### H4
##### H5
###### H6

Body text.
"""
        file_path = tmp_dir / "test.md"
        file_path.write_text(content, encoding="utf-8")

        result = await extractor.extract(file_path)

        # Verify headers are stripped
        assert "# H1" not in result
        assert "## H2" not in result
        assert "### H3" not in result
        assert "Body text" in result

    @pytest.mark.asyncio
    async def test_extract_markdown_lists(self, extractor, tmp_dir):
        """Test markdown list marker stripping."""
        content = """- Item 1
- Item 2
* Bullet 1
* Bullet 2
"""
        file_path = tmp_dir / "test.md"
        file_path.write_text(content, encoding="utf-8")

        result = await extractor.extract(file_path)

        # Verify list markers are stripped
        assert "- Item" not in result
        assert "* Bullet" not in result

    @pytest.mark.asyncio
    async def test_extract_markdown_links(self, extractor, tmp_dir):
        """Test markdown link syntax stripping."""
        content = """[Link text](https://example.com)
[Another link](http://test.org/page)
"""
        file_path = tmp_dir / "test.md"
        file_path.write_text(content, encoding="utf-8")

        result = await extractor.extract(file_path)

        # Verify link syntax is stripped
        assert "[Link text]" not in result
        assert "https://example.com" not in result
        assert "[Another link]" not in result
        assert "http://test.org/page" not in result

    @pytest.mark.asyncio
    async def test_extract_pdf_mocked(self, extractor, tmp_dir, mocker):
        """Test PDF text extraction with mocked pdfplumber library."""
        # Create a mock PDF file
        pdf_path = tmp_dir / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake content")

        # Mock pdfplumber.PDF to simulate page extraction
        # The code uses: with PDF(file_path) as pdf: for page in pdf.pages:
        # So we need a context manager that returns mock_pdf with .pages
        mock_page = mocker.MagicMock()
        mock_page.extract_text.return_value = "Mocked PDF text content."
        mock_pdf = mocker.MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = mocker.MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = mocker.MagicMock(return_value=False)

        # Capture the mock for later assertion
        pdf_mock = mocker.patch("core.text_extractor.PDF", return_value=mock_pdf)

        result = await extractor.extract(pdf_path)

        # Verify mocked PDF extraction path was called
        assert "Mocked PDF text content" in result
        # Verify pdfplumber PDF context manager was used correctly
        pdf_mock.assert_called_once_with(pdf_path)

    @pytest.mark.asyncio
    async def test_extract_docx_custom_document(self, extractor, tmp_dir, mocker):
        """Test DOCX text extraction with custom mocked document."""
        docx_path = tmp_dir / "test.docx"
        docx_path.write_bytes(b"fake docx content")

        # Mock python-docx Document to return custom paragraphs
        mock_document = mocker.MagicMock()
        mock_para1 = mocker.MagicMock()
        mock_para1.text = "First custom paragraph."
        mock_para2 = mocker.MagicMock()
        mock_para2.text = "Second custom paragraph."
        mock_document.paragraphs = [mock_para1, mock_para2]

        # Patch the docx module since Document is imported locally inside _extract_docx
        mock_docx_module = mocker.MagicMock()
        mock_docx_module.Document.return_value = mock_document
        mocker.patch("docx.Document", return_value=mock_document)

        result = await extractor.extract(docx_path)

        # Verify custom DOCX paragraph text was extracted and joined
        assert "First custom paragraph" in result
        assert "Second custom paragraph" in result

    @pytest.mark.asyncio
    async def test_extract_corrupted_pdf(self, extractor, tmp_dir):
        """Test that corrupted/invalid PDF files raise appropriate errors."""
        # Create a file with PDF header but invalid content
        pdf_path = tmp_dir / "corrupted.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 this is not a valid PDF file at all")

        with pytest.raises(TextExtractionError) as exc_info:
            await extractor.extract(pdf_path)

        assert "Failed to extract text from PDF" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_txt_special_characters(self, extractor, tmp_dir):
        """Test that text files with special characters and unicode are handled correctly."""
        # Create a file with special characters and unicode
        txt_path = tmp_dir / "special.txt"
        special_content = """Hello 世界!
Special chars: ñ émojis: 😀🎉
Math: π = 3.14159
Currency: €£¥
Quotes: "hello" 'world'
Accented: café résumé naïve
"""
        txt_path.write_text(special_content, encoding="utf-8")

        result = await extractor.extract(txt_path)

        # Verify special characters and unicode are preserved
        assert "世界" in result
        assert "café" in result
        assert "résumé" in result
        assert "naïve" in result
        assert "émojis" in result
        assert "π" in result
