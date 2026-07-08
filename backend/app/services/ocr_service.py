"""
OCR Service.
Handles image-to-text extraction using Tesseract processing engines.
"""


class OCRService:
    """
    Service class responsible for OCR text extraction routines.
    """

    def extract_text(self, file_path: str) -> str:
        """
        Extract text from a document image or PDF.

        Args:
            file_path (str): Path to the target file.

        Returns:
            str: The extracted plain text content.
        """
        return "Sample extracted text content from OCR stub."
