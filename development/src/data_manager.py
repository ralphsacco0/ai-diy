"""
Data management utilities for AI-DIY application.

Implements overwrite-on-save behavior, CSV schema validation,
and enhanced data validation with fail-fast error handling.
"""

import csv
import json
import logging
import io
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from .api.conventions import (
    validate_csv_headers, CsvConfig, SafetyConfig,
    create_error_response, ApiErrorCode, HTTP_STATUS_MAP
)

logger = logging.getLogger(__name__)


@dataclass
class SaveResult:
    """Result of a save operation."""

    success: bool
    message: str
    id: str
    is_overwrite: bool
    file_path: Path


@dataclass
class ValidationResult:
    """Result of data validation."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]


class DataManager:
    """Manages data operations with overwrite-on-save and validation."""

    def __init__(self, data_root: str = "static/appdocs"):
        self.data_root = Path(data_root)
        self.visions_dir = self.data_root / "visions"
        self.backlog_dir = self.data_root / "backlog"
        self.wireframes_dir = self.backlog_dir / "wireframes"

        # Create directories
        for dir_path in [self.visions_dir, self.backlog_dir, self.wireframes_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def save_vision(self, vision_data: Dict[str, Any], provided_id: Optional[str] = None) -> SaveResult:
        """
        Save vision document with overwrite-on-save behavior.

        Args:
            vision_data: Vision document data
            provided_id: Optional ID for overwrite behavior

        Returns:
            SaveResult with operation details
        """
        try:
            # Validate required fields
            validation = self._validate_vision_data(vision_data)
            if not validation.is_valid:
                raise ValueError(f"Vision validation failed: {'; '.join(validation.errors)}")

            # Determine ID and check for overwrite
            if provided_id:
                vision_id = provided_id
                is_overwrite = (self.visions_dir / f"{vision_id}.json").exists()
            else:
                vision_id = self._generate_vision_id(vision_data.get("title", "Untitled"))
                is_overwrite = False

            # Create vision document with metadata
            vision_doc = {
                **vision_data,
                "id": vision_id,
                "updated_at": datetime.now().isoformat(),
                "created_at": datetime.now().isoformat() if not is_overwrite else vision_data.get("created_at")
            }

            # Validate file size
            json_content = json.dumps(vision_doc, indent=2)
            if len(json_content.encode('utf-8')) > SafetyConfig.MAX_FILE_SIZE_BYTES:
                raise ValueError(f"Vision document too large (max {SafetyConfig.MAX_FILE_SIZE_MB}MB)")

            # Save JSON file
            vision_file = self.visions_dir / f"{vision_id}.json"
            with open(vision_file, 'w') as f:
                f.write(json_content)

            # Create markdown version for readability
            self._create_vision_markdown(vision_doc, vision_file.with_suffix('.md'))

            action = "updated" if is_overwrite else "created"
            logger.info(f"Vision {action}: {vision_id}")

            return SaveResult(
                success=True,
                message=f"Vision '{vision_data.get('title', vision_id)}' {action} successfully",
                id=vision_id,
                is_overwrite=is_overwrite,
                file_path=vision_file
            )

        except Exception as e:
            logger.error(f"Failed to save vision: {e}")
            raise ValueError(f"Vision save failed: {e}")

    def save_backlog_csv(self, csv_content: str, provided_id: Optional[str] = None) -> SaveResult:
        """
        Save backlog CSV with schema validation.

        Args:
            csv_content: CSV content as string
            provided_id: Optional ID for overwrite behavior

        Returns:
            SaveResult with operation details
        """
        try:
            # Validate CSV format and headers
            validation = self._validate_csv_content(csv_content)
            if not validation.is_valid:
                raise ValueError(f"CSV validation failed: {'; '.join(validation.errors)}")

            # Determine ID and check for overwrite
            backlog_id = provided_id or "Backlog"
            csv_file = self.backlog_dir / f"{backlog_id}.csv"
            is_overwrite = csv_file.exists()

            # Save CSV file
            with open(csv_file, 'w', newline='') as f:
                f.write(csv_content)

            # Update metadata
            self._update_backlog_metadata(backlog_id, len(csv_content.splitlines()) - 1)  # -1 for header

            action = "updated" if is_overwrite else "created"
            logger.info(f"Backlog CSV {action}: {backlog_id}")

            return SaveResult(
                success=True,
                message=f"Backlog CSV '{backlog_id}' {action} successfully",
                id=backlog_id,
                is_overwrite=is_overwrite,
                file_path=csv_file
            )

        except Exception as e:
            logger.error(f"Failed to save backlog CSV: {e}")
            raise ValueError(f"Backlog CSV save failed: {e}")

    def get_vision(self, vision_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a vision document by ID."""
        vision_file = self.visions_dir / f"{vision_id}.json"
        if not vision_file.exists():
            return None

        try:
            with open(vision_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read vision {vision_id}: {e}")
            return None

    def list_visions(self) -> List[Dict[str, Any]]:
        """List all vision documents."""
        visions = []
        for vision_file in self.visions_dir.glob("*.json"):
            try:
                with open(vision_file, 'r') as f:
                    vision_doc = json.load(f)
                visions.append(vision_doc)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Skipping invalid vision file {vision_file}: {e}")
                continue

        # Sort by update date, newest first
        visions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return visions

    def delete_vision(self, vision_id: str) -> bool:
        """Delete a vision document and its markdown version."""
        vision_file = self.visions_dir / f"{vision_id}.json"
        md_file = self.visions_dir / f"{vision_id}.md"

        deleted = False
        if vision_file.exists():
            vision_file.unlink()
            deleted = True
        if md_file.exists():
            md_file.unlink()
            deleted = True

        if deleted:
            logger.info(f"Vision deleted: {vision_id}")

        return deleted

    def _validate_vision_data(self, vision_data: Dict[str, Any]) -> ValidationResult:
        """Validate vision document data."""
        errors = []
        warnings = []

        # Required fields
        if not vision_data.get("title"):
            errors.append("title is required")
        if not vision_data.get("content"):
            errors.append("content is required")

        # Optional fields validation
        if "client_approval" in vision_data:
            if not isinstance(vision_data["client_approval"], bool):
                errors.append("client_approval must be boolean")

        # Content length warning
        content = vision_data.get("content", "")
        if len(content) > 10000:  # 10KB warning threshold
            warnings.append("content is very large (>10KB)")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _validate_csv_content(self, csv_content: str) -> ValidationResult:
        """Validate CSV content and schema."""
        errors = []
        warnings = []

        if not csv_content.strip():
            errors.append("CSV content is empty")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        try:
            # Parse CSV to check format
            csv_reader = csv.reader(io.StringIO(csv_content))
            rows = list(csv_reader)

            if not rows:
                errors.append("CSV has no data")
                return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

            headers = rows[0]

            # Validate headers against canonical schema
            is_valid, error_msg = validate_csv_headers(headers)
            if not is_valid:
                errors.append(error_msg)

            # Check for reasonable row count
            if len(rows) > 1000:  # Arbitrary limit for safety
                warnings.append(f"CSV has {len(rows)} rows (including header)")

            # Validate data rows have correct column count
            expected_cols = len(CsvConfig.CANONICAL_HEADERS)
            for i, row in enumerate(rows[1:], 2):  # Start from row 2 (after header)
                if len(row) != expected_cols:
                    errors.append(f"Row {i} has {len(row)} columns, expected {expected_cols}")

        except csv.Error as e:
            errors.append(f"CSV parsing error: {e}")
        except Exception as e:
            errors.append(f"CSV validation error: {e}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _generate_vision_id(self, title: str) -> str:
        """Generate a safe ID from vision title."""
        from .api.conventions import generate_id_from_title

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return generate_id_from_title(title, timestamp)

    def _create_vision_markdown(self, vision_doc: Dict[str, Any], md_file: Path) -> None:
        """Create markdown version of vision document."""
        with open(md_file, 'w') as f:
            f.write(f"# {vision_doc.get('title', 'Untitled Vision')}\n\n")
            f.write(f"**ID:** {vision_doc['id']}\n")
            f.write(f"**Status:** {vision_doc.get('status', 'draft').title()}\n")
            f.write(f"**Created:** {vision_doc.get('created_at', 'Unknown')}\n")
            f.write(f"**Updated:** {vision_doc.get('updated_at', 'Unknown')}\n")
            f.write(f"**Client Approval:** {'Yes' if vision_doc.get('client_approval') else 'No'}\n\n")
            f.write("---\n\n")
            f.write(vision_doc.get('content', ''))

    def _update_backlog_metadata(self, backlog_id: str, row_count: int) -> None:
        """Update backlog metadata JSON file."""
        metadata_file = self.backlog_dir / f"{backlog_id}.json"

        metadata = {
            "id": backlog_id,
            "last_updated": datetime.now().isoformat(),
            "row_count": row_count,
            "wireframes": []
        }

        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)


class CsvValidator:
    """Specialized CSV validation utilities."""

    @staticmethod
    def validate_csv_file(file_path: Path) -> Tuple[bool, List[str]]:
        """Validate a CSV file against canonical schema."""
        try:
            with open(file_path, 'r') as f:
                csv_content = f.read()

            manager = DataManager()
            validation = manager._validate_csv_content(csv_content)

            return validation.is_valid, validation.errors + validation.warnings

        except IOError as e:
            return False, [f"Cannot read CSV file: {e}"]
        except Exception as e:
            return False, [f"CSV validation error: {e}"]

    @staticmethod
    def get_csv_headers(file_path: Path) -> Optional[List[str]]:
        """Get headers from CSV file."""
        try:
            with open(file_path, 'r') as f:
                reader = csv.reader(f)
                return next(reader, None)
        except Exception:
            return None


# Global data manager instance
data_manager = DataManager()


def validate_and_save_vision(vision_data: Dict[str, Any], provided_id: Optional[str] = None) -> SaveResult:
    """Validate and save vision with overwrite-on-save behavior."""
    return data_manager.save_vision(vision_data, provided_id)


def validate_and_save_backlog_csv(csv_content: str, provided_id: Optional[str] = None) -> SaveResult:
    """Validate CSV and save backlog with overwrite-on-save behavior."""
    return data_manager.save_backlog_csv(csv_content, provided_id)


def get_vision_document(vision_id: str) -> Optional[Dict[str, Any]]:
    """Get vision document by ID."""
    return data_manager.get_vision(vision_id)


def list_vision_documents() -> List[Dict[str, Any]]:
    """List all vision documents."""
    return data_manager.list_visions()


def delete_vision_document(vision_id: str) -> bool:
    """Delete vision document."""
    return data_manager.delete_vision(vision_id)