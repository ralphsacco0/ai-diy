"""
Shared project context extraction utilities.

Used by both Sprint Review Alex (debugging) and Sprint Execution Mike (building)
to understand the current state of a project in the execution sandbox.

Extracts:
- File structure with exports (functions, classes, constants)
- API endpoints from route files
- Database schema by querying actual SQLite database
- Code patterns from existing files

NOTE: These methods are copied from Mike's superior extraction logic in sprint_orchestrator.py
to provide accurate, database-querying context instead of just parsing static code.
"""
import re
import logging
import sqlite3
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


def extract_exports_from_file(file_path: Path) -> List[str]:
    """
    Extract exported functions/constants from a JavaScript file.

    Handles:
    - export function name(...)
    - export async function name(...)
    - export class name
    - export const/let/var name = ...
    - export { name1, name2 }
    - export default

    Args:
        file_path: Path to JavaScript file

    Returns:
        List of exported names (sorted, deduplicated)
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        exports = []

        # Remove comments to avoid false positives
        # Remove single-line comments
        content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        # Match: export function name(...) or export async function name(...)
        exports.extend(re.findall(r'export\s+(?:async\s+)?function\s+(\w+)', content))

        # Match: export class name
        exports.extend(re.findall(r'export\s+class\s+(\w+)', content))

        # Match: export const name = or export let name =
        exports.extend(re.findall(r'export\s+(?:const|let|var)\s+(\w+)', content))

        # Match: export { name1, name2 } (including re-exports)
        export_blocks = re.findall(r'export\s*\{([^}]+)\}', content)
        for block in export_blocks:
            names = [name.strip().split(' as ')[0].split(' from ')[0] for name in block.split(',')]
            exports.extend([n.strip() for n in names if n.strip()])

        # Match: export default (note as 'default')
        if re.search(r'export\s+default', content):
            exports.append('default')

        return sorted(set(exports))  # Remove duplicates and sort
    except Exception as e:
        logger.debug(f"Could not extract exports from {file_path}: {e}")
        return []


def extract_file_structure(project_path: Path) -> str:
    """
    Get organized file structure with exported functions.

    Scans the project and categorizes files by type (controllers, models, routes, etc.),
    showing exported functions/classes from each file.

    Args:
        project_path: Root path of the project

    Returns:
        Formatted string showing file structure with exports
    """
    try:
        structure = {
            'controllers': [],
            'models': [],
            'routes': [],
            'components': [],
            'services': [],
            'middleware': []
        }

        # Scan for files and extract exports
        for js_file in project_path.glob("src/**/*.js"):
            rel_path = js_file.relative_to(project_path)
            path_str = str(rel_path)

            # Extract exports from this file
            exports = extract_exports_from_file(js_file)
            file_info = {
                'path': path_str,
                'exports': exports
            }

            if 'controllers' in path_str:
                structure['controllers'].append(file_info)
            elif 'models' in path_str:
                structure['models'].append(file_info)
            elif 'routes' in path_str:
                structure['routes'].append(file_info)
            elif 'components' in path_str:
                structure['components'].append(file_info)
            elif 'services' in path_str:
                structure['services'].append(file_info)
            elif 'middleware' in path_str:
                structure['middleware'].append(file_info)

        # Format output with exports
        result = []
        for category, files in structure.items():
            if files:
                result.append(f"\n{category.upper()}:")
                for file_info in files[:5]:  # Show up to 5 files per category
                    exports_str = ', '.join(file_info['exports'][:10]) if file_info['exports'] else 'no exports'
                    if len(file_info['exports']) > 10:
                        exports_str += f' (+{len(file_info["exports"]) - 10} more)'
                    result.append(f"  - {file_info['path']}")
                    result.append(f"    Exports: {exports_str}")
                if len(files) > 5:
                    result.append(f"  (+{len(files) - 5} more files)")

        if result:
            return "Current file structure with exports:\n" + "\n".join(result)
        else:
            return "No files found yet (first story)"
    except Exception as e:
        logger.warning(f"Could not extract file structure: {e}")
        return "Could not extract file structure"


def extract_api_endpoints(project_path: Path) -> str:
    """
    Parse API endpoints from route files.

    Looks for Express router patterns like:
    - router.get('/path', ...)
    - router.post('/path', ...)

    Args:
        project_path: Root path of the project

    Returns:
        Formatted string showing API endpoints
    """
    try:
        endpoints = []

        # Look for route files
        route_files = list(project_path.glob("src/routes/*.js"))

        for route_file in route_files[:5]:  # Limit to first 5 files
            content = route_file.read_text(encoding="utf-8")
            # Extract router.get, router.post, etc.
            methods = re.findall(r"router\.(get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]", content)
            for method, path in methods:
                endpoints.append(f"- {method.upper()} {path}")

        if endpoints:
            return "Current API endpoints:\n" + "\n".join(endpoints)
        else:
            return "No API endpoints found yet (first story)"
    except Exception as e:
        logger.warning(f"Could not extract API endpoints: {e}")
        return "Could not extract API endpoints"


def extract_database_schema(project_path: Path) -> str:
    """
    Extract actual database schema by querying the SQLite database directly.

    This is Mike's SUPERIOR approach - queries the actual database with PRAGMA
    instead of just parsing CREATE TABLE statements from code.

    Looks for:
    - Actual database file (data.sqlite) and queries it with PRAGMA table_info
    - Falls back to CREATE TABLE statements in db.js if database doesn't exist yet

    Args:
        project_path: Root path of the project

    Returns:
        Formatted string showing database schema with row counts
    """
    try:
        schema_info = []

        # First, try to query the actual database file
        db_path = project_path / "data.sqlite"
        if db_path.exists():
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()

                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                tables = cursor.fetchall()

                for (table_name,) in tables:
                    # Get actual column info using PRAGMA
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()

                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]

                    # Format column info
                    col_lines = []
                    for col in columns:
                        # col = (cid, name, type, notnull, dflt_value, pk)
                        col_name = col[1]
                        col_type = col[2]
                        col_notnull = " NOT NULL" if col[3] else ""
                        col_default = f" DEFAULT {col[4]}" if col[4] is not None else ""
                        col_pk = " PRIMARY KEY" if col[5] else ""
                        col_lines.append(f"    {col_name} {col_type}{col_notnull}{col_default}{col_pk}")

                    schema_info.append(f"- Table '{table_name}' ({row_count} rows):\n" + "\n".join(col_lines))

                conn.close()

                if schema_info:
                    return "🗄️ ACTUAL DATABASE SCHEMA (from data.sqlite):\n" + "\n".join(schema_info)
            except sqlite3.Error as db_err:
                logger.warning(f"Could not query database: {db_err}")
                # Fall through to code-based extraction

        # Fallback: Parse CREATE TABLE from code if database doesn't exist or query failed
        db_file = project_path / "src" / "db.js"
        if db_file.exists():
            content = db_file.read_text(encoding="utf-8")
            # Extract CREATE TABLE statements
            tables = re.findall(r'CREATE TABLE IF NOT EXISTS (\w+)\s*\((.*?)\)', content, re.DOTALL)
            for table_name, table_def in tables:
                # Clean up the table definition
                cleaned_def = "\n".join([f"    {line.strip()}" for line in table_def.split("\n") if line.strip()])
                schema_info.append(f"- Table '{table_name}' (from code - database not yet created):\n{cleaned_def[:300]}")

        if schema_info:
            return "📝 DATABASE SCHEMA (from code - not yet created):\n" + "\n".join(schema_info)
        else:
            return "No database schema found yet (first story)"
    except Exception as e:
        logger.warning(f"Could not extract database schema: {e}")
        return "Could not extract database schema"


def extract_code_patterns(project_path: Path) -> str:
    """
    Analyze code patterns from existing files.

    Looks at existing controllers and routes to identify:
    - Error handling patterns (try/catch)
    - Response format patterns
    - Async patterns (async/await)
    - Middleware patterns

    Args:
        project_path: Root path of the project

    Returns:
        Formatted string showing established code patterns
    """
    try:
        patterns = []

        # Look at existing controllers to find patterns
        controller_files = list(project_path.glob("src/controllers/*.js"))
        if controller_files:
            content = controller_files[0].read_text(encoding="utf-8")

            # Check for error handling pattern
            if "try {" in content and "catch" in content:
                patterns.append("- Error handling: try/catch blocks")
            if "res.status" in content:
                patterns.append("- Response format: res.status(code).json({...})")
            if "req.body" in content:
                patterns.append("- Request parsing: req.body")
            if "async" in content:
                patterns.append("- Async pattern: async/await")

        # Look at existing routes
        route_files = list(project_path.glob("src/routes/*.js"))
        if route_files:
            content = route_files[0].read_text(encoding="utf-8")
            if "router.use" in content:
                patterns.append("- Middleware: router.use() for middleware")

        if patterns:
            return "Established code patterns:\n" + "\n".join(patterns)
        else:
            return "No established patterns yet (first story)"
    except Exception as e:
        logger.warning(f"Could not extract code patterns: {e}")
        return "Could not extract code patterns"
