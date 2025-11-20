"""
Utility helpers for converting uploaded files into normalized paper entries.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog

from ..shared.field_mapping import normalize_paper_fields
from ..shared.session_folder_manager import get_session_folder
from .export_tools import save_papers_to_csv

logger = structlog.get_logger(__name__)

try:
    from pypdf import PdfReader  # type: ignore
except Exception:
    try:
        from PyPDF2 import PdfReader  # type: ignore
    except Exception:  # pragma: no cover - optional dependency
        PdfReader = None


def ingest_uploaded_documents(
    files: List[Dict[str, Any]],
    session_id: str,
    topic: Optional[str] = None,
    file_prefix: str = "uploaded_papers",
) -> Dict[str, Any]:
    """Convert uploaded files into normalized paper entries stored under the session folder."""

    if not files:
        return {"status": "error", "error": "No files provided for ingestion"}

    session_folder = Path(get_session_folder(session_id, topic))
    uploads_dir = session_folder / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    papers_info_path = session_folder / "papers_info.json"
    papers_info: Dict[str, Any] = {}
    if papers_info_path.exists():
        try:
            with papers_info_path.open("r", encoding="utf-8") as fh:
                papers_info = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load existing papers_info.json", error=str(exc))
            papers_info = {}

    processed_papers: List[Dict[str, Any]] = []
    uploaded_files: List[Dict[str, Any]] = []

    for index, file_data in enumerate(files, start=1):
        try:
            processed = _process_single_file(
                file_data=file_data,
                uploads_dir=uploads_dir,
                session_id=session_id,
                topic=topic,
                order=index,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(
                "Failed to process uploaded file",
                filename=file_data.get("filename"),
                error=str(exc),
            )
            continue

        if not processed:
            continue

        paper_entry, file_record = processed
        papers_info[paper_entry["paper_id"]] = paper_entry
        processed_papers.append(paper_entry)
        uploaded_files.append(file_record)

    if not processed_papers:
        return {"status": "error", "error": "Failed to process uploaded files"}

    try:
        with papers_info_path.open("w", encoding="utf-8") as fh:
            json.dump(papers_info, fh, indent=2, ensure_ascii=False)
    except OSError as exc:
        logger.error("Failed to write papers_info.json", error=str(exc))

    csv_result = save_papers_to_csv(
        papers=processed_papers,
        session_id=session_id,
        topic=topic or "upload",  # 🆕 上传文件的 topic 标记为 "upload"
        file_prefix=file_prefix,
        append_mode=True,  # 启用追加模式，合并到 all_papers.csv
    )

    return {
        "status": "success",
        "papers": processed_papers,
        "session_id": session_id,
        "topic": topic,
        "csv_result": csv_result,
        "papers_info_path": str(papers_info_path),
        "uploaded_files": uploaded_files,
    }


def _process_single_file(
    file_data: Dict[str, Any],
    uploads_dir: Path,
    session_id: str,
    topic: Optional[str],
    order: int,
) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """Handle a single uploaded file and return normalized paper data plus file metadata."""

    filename = file_data.get("filename") or file_data.get("name") or f"uploaded_{order}.txt"
    encoding = (file_data.get("encoding") or file_data.get("contentEncoding") or "").lower()
    mime_type = file_data.get("mime_type") or file_data.get("content_type")
    content = file_data.get("content")

    if not isinstance(content, str) or not content.strip():
        logger.warning("Uploaded file has no content", filename=filename)
        return None

    safe_name = _sanitize_filename(filename) or f"uploaded_{order}.txt"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    target_path = uploads_dir / safe_name

    file_bytes: Optional[bytes] = None
    text_content = ""
    file_already_exists = target_path.exists()

    # 🆕 如果文件已存在，检查是否需要重新保存
    if file_already_exists:
        logger.info(f"📄 File already exists: {target_path.name}, checking if re-save is needed...")

        # 如果是 base64 编码，解码后比较内容
        if encoding == "base64":
            try:
                file_bytes = base64.b64decode(content, validate=False)
                existing_bytes = target_path.read_bytes()

                # 如果内容完全相同，跳过保存，直接提取文本
                if file_bytes == existing_bytes:
                    logger.info(f"✅ File content identical, skipping save: {target_path.name}")
                    text_content = _extract_text_from_binary(file_bytes, safe_name, mime_type)
                    file_bytes = None  # 标记为不需要保存
                else:
                    # 内容不同，添加序号保存新文件
                    logger.info(f"⚠️ File content different, saving as new file...")
                    base_name = target_path.stem
                    suffix = target_path.suffix
                    counter = 1
                    while target_path.exists():
                        target_path = uploads_dir / f"{base_name}_{counter}{suffix}"
                        counter += 1
                    logger.info(f"Using new name: {target_path.name}")
            except Exception as exc:
                logger.warning("Failed to decode base64 content; treating as text", filename=filename, error=str(exc))
                file_bytes = None
        elif _looks_like_base64(content):
            try:
                file_bytes = base64.b64decode(content, validate=False)
                existing_bytes = target_path.read_bytes()

                if file_bytes == existing_bytes:
                    logger.info(f"✅ File content identical, skipping save: {target_path.name}")
                    text_content = _extract_text_from_binary(file_bytes, safe_name, mime_type)
                    file_bytes = None
                else:
                    base_name = target_path.stem
                    suffix = target_path.suffix
                    counter = 1
                    while target_path.exists():
                        target_path = uploads_dir / f"{base_name}_{counter}{suffix}"
                        counter += 1
                    logger.info(f"Using new name: {target_path.name}")
            except Exception:
                file_bytes = None
        else:
            # 文本文件，比较内容
            existing_text = target_path.read_text(encoding="utf-8", errors="ignore")
            if content == existing_text:
                logger.info(f"✅ File content identical, skipping save: {target_path.name}")
                text_content = content
            else:
                base_name = target_path.stem
                suffix = target_path.suffix
                counter = 1
                while target_path.exists():
                    target_path = uploads_dir / f"{base_name}_{counter}{suffix}"
                    counter += 1
                logger.info(f"Using new name: {target_path.name}")
    else:
        # 文件不存在，正常解码
        if encoding == "base64":
            try:
                file_bytes = base64.b64decode(content, validate=False)
            except Exception as exc:
                logger.warning("Failed to decode base64 content; treating as text", filename=filename, error=str(exc))
                file_bytes = None
        elif _looks_like_base64(content):
            try:
                file_bytes = base64.b64decode(content, validate=False)
            except Exception:
                file_bytes = None

    # 只有在需要保存时才写入文件
    if file_bytes is not None and not text_content:
        target_path.write_bytes(file_bytes)
        text_content = _extract_text_from_binary(file_bytes, safe_name, mime_type)
        logger.info(f"💾 Saved binary file: {target_path.name}")
    elif not text_content:
        target_path.write_text(content, encoding="utf-8", errors="ignore")
        text_content = content
        logger.info(f"💾 Saved text file: {target_path.name}")

    if not text_content.strip():
        text_content = f"用户上传的文件（{filename}）已保存，暂未自动提取文本内容。"

    summary_text = _summarize_text(text_content)
    paper_id = _generate_upload_paper_id(session_id, filename, order, text_content)
    published = datetime.now().strftime("%Y-%m-%d")
    relative_path = _relative_path(target_path)

    raw_entry = {
        "paper_id": paper_id,
        "title": Path(filename).stem or paper_id,
        "authors": file_data.get("authors", []),
        "abstract": summary_text,
        "summary": summary_text,
        "content": text_content,
        "full_text": text_content,
        "url": relative_path,
        "pdf_url": "",
        "published": published,
        "source": "upload",
        "categories": file_data.get("categories", []),
        "score": file_data.get("score"),
        "uploaded_at": datetime.now().isoformat(),
        "upload_metadata": {
            "filename": filename,
            "saved_path": relative_path,
            "mime_type": mime_type,
            "encoding": encoding or "utf-8",
            "session_id": session_id,
            "topic": topic,
        },
    }

    normalized = normalize_paper_fields(raw_entry, source="upload")
    normalized.update(
        {
            "summary": summary_text,
            "content": text_content,
            "full_text": text_content,
            "upload_metadata": raw_entry["upload_metadata"],
            "local_file": relative_path,
        }
    )

    file_record = {
        "paper_id": paper_id,
        "filename": filename,
        "saved_path": relative_path,
        "mime_type": mime_type,
        "encoding": encoding or "utf-8",
    }

    logger.info(
        "Processed uploaded document",
        filename=filename,
        paper_id=paper_id,
        saved_path=relative_path,
    )

    return normalized, file_record


def _sanitize_filename(filename: str) -> str:
    sanitized = re.sub(r'[<>:"/\\|?*]+', "_", filename)
    sanitized = re.sub(r'[\s_]+', "_", sanitized)
    sanitized = sanitized.strip("_")
    if not sanitized:
        sanitized = "uploaded_document"
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    return sanitized


def _looks_like_base64(value: str) -> bool:
    stripped = value.strip()
    if len(stripped) < 64 or len(stripped) % 4 != 0:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9+/=\r\n]+", stripped))


def _generate_upload_paper_id(session_id: str, filename: str, order: int, content: str) -> str:
    digest = hashlib.md5(f"{session_id}:{filename}:{order}:{content[:200]}".encode("utf-8", errors="ignore")).hexdigest()
    return f"upload_{digest[:12]}"


def _summarize_text(text: str, limit: int = 1500) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) > limit:
        return cleaned[:limit] + "... (truncated)"
    return cleaned


def _extract_text_from_binary(data: bytes, filename: str, mime_type: Optional[str]) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf" or (mime_type and "pdf" in mime_type.lower()):
        text = _extract_pdf_text(data)
        if not text or len(text.strip()) < 50:
            # If PDF extraction failed or got minimal text, try alternative methods
            try:
                # Try to decode as text as fallback
                text = data.decode("utf-8", errors="ignore")
                if len(text.strip()) < 50:
                    text = "（PDF 内容已保存，但未提取到足够文本内容。）"
            except Exception:
                text = "（PDF 内容已保存，但未提取到文本内容。）"
        return text

    if suffix == ".docx" or (mime_type and "wordprocessingml" in mime_type.lower()):
        return _extract_docx_text(data)

    if suffix in {".txt", ".md", ".csv", ".json"}:
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return data.decode("latin-1", errors="ignore")

    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _extract_pdf_text(data: bytes) -> str:
    # First try pypdf/PyPDF2 backend if available
    if PdfReader is not None:
        try:
            logger.info(f"Attempting to extract text from PDF ({len(data)} bytes) via PdfReader")
            reader = PdfReader(BytesIO(data))
            # Attempt to decrypt with empty password if encrypted (best-effort)
            try:
                if getattr(reader, "is_encrypted", False):
                    logger.info("PDF is encrypted; attempting empty-password decrypt")
                    reader.decrypt("")
            except Exception:
                pass

            texts = []
            pages = getattr(reader, "pages", [])
            logger.info(f"PDF loaded successfully, total pages: {len(pages)}")
            for page_idx, page in enumerate(pages):
                try:
                    page_text = page.extract_text() or ""
                    if page_text:
                        texts.append(page_text)
                        logger.debug(f"Extracted {len(page_text)} characters from page {page_idx + 1}")
                    else:
                        logger.debug(f"No text extracted from page {page_idx + 1}")
                except Exception as page_exc:
                    logger.warning(f"Failed to extract text from page {page_idx + 1}", error=str(page_exc))
                    continue

            joined = "\n".join(texts).strip()
            bad_char_ratio = (joined.count("\uFFFD") / max(len(joined), 1)) if joined else 0.0
            if joined and len(joined) >= 50 and bad_char_ratio < 0.05:
                logger.info(f"Successfully extracted {len(joined)} characters from PDF via PdfReader")
                return joined
            else:
                logger.warning("PdfReader extraction empty/short or garbled; trying pdfminer fallback")
        except Exception as exc:
            logger.warning("PdfReader backend failed; trying pdfminer fallback", error=str(exc))

    # Fallback to pdfminer.six if available (better CJK handling)
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract_text  # type: ignore
        logger.info("Attempting PDF text extraction via pdfminer.six")
        text = pdfminer_extract_text(BytesIO(data)) or ""
        text = text.strip()
        if text:
            logger.info(f"Successfully extracted {len(text)} characters from PDF via pdfminer.six")
            return text
        else:
            logger.warning("pdfminer.six returned empty text")
    except Exception as exc:
        logger.warning("pdfminer.six not available or failed", error=str(exc))

    # Final fallback: informative message
    return "（PDF 内容已保存，但未提取到文本。）"


def _extract_docx_text(data: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(data)) as zf:
            with zf.open("word/document.xml") as doc_xml:
                xml_content = doc_xml.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        logger.warning("Failed to open DOCX", error=str(exc))
        return "（DOCX 内容已保存，暂未提取文本。）"

    try:
        from xml.etree import ElementTree as ET  # noqa: PLC0415

        namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        tree = ET.fromstring(xml_content)
        paragraphs = [elem.text or "" for elem in tree.iter(f"{namespace}t")]
        text = "\n".join(paragraphs).strip()
        return text or "（DOCX 内容已保存，但未提取到文本。）"
    except Exception as exc:
        logger.warning("Failed to parse DOCX XML", error=str(exc))
        return "（DOCX 内容已保存，文本提取失败。）"


def _relative_path(path: Path) -> str:
    try:
        rel = path.relative_to(Path(".").resolve())
    except ValueError:
        rel = path
    return str(rel).replace("\\", "/")
