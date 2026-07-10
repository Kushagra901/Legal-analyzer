# ocr_service.py
"""
OCR Service.
Handles image-to-text extraction using Tesseract processing engines,
with a native PDF text extraction path.
"""
import io
import os
from pypdf import PdfReader
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

class OCRService:
    """
    Service class responsible for OCR and native text extraction routines.
    """

    def __init__(self) -> None:
        """
        Initializes OCRService, configuring the tesseract executable path for Windows.
        """
        self.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(self.tesseract_cmd):
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    def should_use_ocr(self, native_text: str) -> bool:
        """
        Determines if OCR should be used based on characters extracted natively.
        If native text extraction yields fewer than 200 characters, we fall back to OCR.

        Args:
            native_text (str): The text extracted using native PDF extraction methods.

        Returns:
            bool: True if OCR should be run, False otherwise.

        Threshold Selection:
            We chose 200 characters because scanned PDF documents or image-only documents
            usually yield 0 characters or a very small amount of junk noise/metadata
            (e.g., margins, page numbers, or watermark text like 'Scanned with CamScanner').
            200 characters is a safe upper limit to filter out scanner artifacts while
            avoiding unnecessary CPU-heavy OCR processing on legitimate text-rich PDFs.
        """
        cleaned = native_text.strip() if native_text else ""
        return len(cleaned) < 200

    def extract_text_natively(self, file_source: str | bytes) -> str:
        """
        Extract text from a PDF file using pypdf reader.

        Args:
            file_source (str | bytes): Path to the target PDF or raw PDF bytes.

        Returns:
            str: The extracted plain text content.
        """
        try:
            if isinstance(file_source, bytes):
                reader = PdfReader(io.BytesIO(file_source))
            else:
                reader = PdfReader(file_source)

            text_parts = []
            for page in reader.pages:
                text_content = page.extract_text()
                if text_content:
                    text_parts.append(text_content)
            return "\n".join(text_parts)
        except Exception as e:
            print(f"Error during native text extraction: {e}")
            return ""

    def extract_text_via_ocr(self, file_source: str | bytes) -> str:
        """
        Perform OCR on PDF pages by rendering them to images using PyMuPDF (fitz)
        and running Tesseract OCR.

        Args:
            file_source (str | bytes): Path to the target PDF or raw PDF bytes.

        Returns:
            str: The extracted plain text content via OCR.
        """
        try:
            if isinstance(file_source, bytes):
                doc = fitz.open(stream=file_source, filetype="pdf")
            else:
                doc = fitz.open(file_source)

            ocr_parts = []
            for page in doc:
                # Render page to image bytes (PNG format)
                pix = page.get_pixmap()
                img_bytes = pix.tobytes("png")
                
                # Load image in PIL and execute OCR
                img = Image.open(io.BytesIO(img_bytes))
                text = pytesseract.image_to_string(img)
                if text:
                    ocr_parts.append(text)
            return "\n".join(ocr_parts)
        except Exception as e:
            print(f"Error during OCR text extraction: {e}")
            return ""

    def process_document(self, file_source: str | bytes) -> tuple[str, str]:
        """
        Processes a document, determines whether to use native text extraction
        or fall back to OCR, and returns a tuple of (extracted_text, method_used).

        Args:
            file_source (str | bytes): Path to the target PDF or raw PDF bytes.

        Returns:
            tuple[str, str]: Tuple of (extracted_text, method_used).
                             method_used can be either "native" or "ocr".
        """
        # 1. Try native extraction
        native_text = self.extract_text_natively(file_source)
        
        # 2. Apply fallback check
        if self.should_use_ocr(native_text):
            print(f"Native extraction returned {len(native_text)} characters. Running OCR fallback...")
            ocr_text = self.extract_text_via_ocr(file_source)
            return ocr_text, "ocr"
        else:
            print(f"Native extraction returned {len(native_text)} characters. Using native text.")
            return native_text, "native"

    def extract_text(self, file_path: str) -> str:
        """
        Extract text from a document image or PDF using the unified process_document path.
        Deprecated: Use process_document instead for method tracing.
        """
        text_content, _ = self.process_document(file_path)
        return text_content

