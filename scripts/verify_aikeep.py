#!/usr/bin/env python3
"""
Verification script for \aikeep{} and \aianchor{} annotations in LaTeX files.

This script extracts all \aikeep{...} and \aianchor{...} protected content
from LaTeX files, generates a manifest with SHA-256 hashes, and can verify
that protected content has not been modified.

Usage:
    python scripts/verify_aikeep.py generate    # Generate manifest
    python scripts/verify_aikeep.py verify      # Verify against manifest
    python scripts/verify_aikeep.py list        # List all protected content
    python scripts/verify_aikeep.py diff        # Show changes since manifest
"""

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterator


@dataclass
class ProtectedBlock:
    """Represents a single protected block (\aikeep{} or \aianchor{})."""
    file: str
    line: int
    content: str
    hash: str
    block_type: str  # 'aikeep' or 'aianchor'

    @classmethod
    def from_content(cls, file: str, line: int, content: str, block_type: str = 'aikeep') -> "ProtectedBlock":
        """Create a ProtectedBlock with computed hash."""
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
        return cls(file=file, line=line, content=content, hash=content_hash, block_type=block_type)


# Backwards compatibility alias
AiKeepBlock = ProtectedBlock


def extract_braced_content(text: str, start_pos: int) -> tuple[str, int]:
    """
    Extract content within braces, handling nested braces.

    Args:
        text: The full text to parse
        start_pos: Position of the opening brace '{'

    Returns:
        Tuple of (extracted content without outer braces, end position)
    """
    if text[start_pos] != '{':
        raise ValueError(f"Expected '{{' at position {start_pos}")

    depth = 1
    pos = start_pos + 1
    content_start = pos

    while pos < len(text) and depth > 0:
        char = text[pos]
        if char == '\\' and pos + 1 < len(text):
            # Skip escaped characters
            pos += 2
            continue
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
        pos += 1

    if depth != 0:
        raise ValueError(f"Unmatched braces starting at position {start_pos}")

    # pos now points just after the closing brace
    return text[content_start:pos-1], pos


def find_protected_blocks(content: str, filepath: str) -> Iterator[ProtectedBlock]:
    """
    Find all \aikeep{...} and \aianchor{...} blocks in the given content.

    Args:
        content: LaTeX file content
        filepath: Path to the file (for reporting)

    Yields:
        ProtectedBlock instances for each found block
    """
    # Pattern to find \aikeep or \aianchor followed by {
    pattern = re.compile(r'\\(aikeep|aianchor)\s*\{')

    # Pattern to detect command definitions (skip these)
    definition_pattern = re.compile(r'\\newcommand\{\\(aikeep|aianchor)\}')

    # Track line numbers
    lines = content.split('\n')
    line_starts = [0]
    for line in lines[:-1]:
        line_starts.append(line_starts[-1] + len(line) + 1)

    def pos_to_line(pos: int) -> int:
        """Convert character position to line number (1-indexed)."""
        for i, start in enumerate(line_starts):
            if i + 1 < len(line_starts) and line_starts[i + 1] > pos:
                return i + 1
            elif i + 1 == len(line_starts) and start <= pos:
                return i + 1
        return len(lines)

    for match in pattern.finditer(content):
        # Extract the block type from the match
        block_type = match.group(1)  # 'aikeep' or 'aianchor'

        # Find the opening brace position
        brace_pos = match.end() - 1
        line_num = pos_to_line(match.start())

        # Get the line content to check if it's a definition or comment
        line_start = content.rfind('\n', 0, match.start()) + 1
        line_end = content.find('\n', match.start())
        if line_end == -1:
            line_end = len(content)
        line_content = content[line_start:line_end]

        # Skip if this is within a command definition or a comment line
        if definition_pattern.search(line_content):
            continue
        if line_content.lstrip().startswith('%'):
            continue

        try:
            protected_content, _ = extract_braced_content(content, brace_pos)
            yield ProtectedBlock.from_content(filepath, line_num, protected_content, block_type)
        except ValueError as e:
            print(f"Warning: {filepath}:{line_num}: {e}", file=sys.stderr)


# Backwards compatibility alias
find_aikeep_blocks = find_protected_blocks


def scan_tex_files(root_dir: Path) -> list[ProtectedBlock]:
    """
    Scan all .tex files in the directory tree for \aikeep and \aianchor blocks.

    Args:
        root_dir: Root directory to scan

    Returns:
        List of all found ProtectedBlock instances
    """
    blocks = []

    # Find all .tex files
    tex_files = list(root_dir.glob('**/*.tex'))

    for tex_file in sorted(tex_files):
        rel_path = tex_file.relative_to(root_dir)
        try:
            content = tex_file.read_text(encoding='utf-8')
            for block in find_protected_blocks(content, str(rel_path)):
                blocks.append(block)
        except Exception as e:
            print(f"Error reading {rel_path}: {e}", file=sys.stderr)

    return blocks


def generate_manifest(root_dir: Path, manifest_path: Path) -> list[ProtectedBlock]:
    """
    Generate a manifest file containing all protected blocks and their hashes.

    Args:
        root_dir: Root directory to scan
        manifest_path: Path to write the manifest

    Returns:
        List of found blocks
    """
    blocks = scan_tex_files(root_dir)

    # Count by type
    aikeep_count = sum(1 for b in blocks if b.block_type == 'aikeep')
    aianchor_count = sum(1 for b in blocks if b.block_type == 'aianchor')

    manifest = {
        "version": 2,
        "description": "AI-protected content manifest for \\aikeep{} and \\aianchor{} blocks",
        "total_blocks": len(blocks),
        "aikeep_count": aikeep_count,
        "aianchor_count": aianchor_count,
        "blocks": [asdict(b) for b in blocks]
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"Generated manifest with {len(blocks)} protected block(s)")
    print(f"  - \\aikeep blocks: {aikeep_count}")
    print(f"  - \\aianchor blocks: {aianchor_count}")
    print(f"Manifest saved to: {manifest_path}")

    return blocks


def load_manifest(manifest_path: Path) -> list[ProtectedBlock]:
    """
    Load blocks from a manifest file.

    Args:
        manifest_path: Path to the manifest file

    Returns:
        List of ProtectedBlock instances
    """
    with open(manifest_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle both v1 (without block_type) and v2 (with block_type) manifests
    blocks = []
    for b in data["blocks"]:
        if "block_type" not in b:
            b["block_type"] = "aikeep"  # Default for legacy manifests
        blocks.append(ProtectedBlock(**b))
    return blocks


def verify_manifest(root_dir: Path, manifest_path: Path) -> bool:
    """
    Verify current files against the manifest.

    Args:
        root_dir: Root directory to scan
        manifest_path: Path to the manifest file

    Returns:
        True if verification passes, False otherwise
    """
    if not manifest_path.exists():
        print(f"Error: Manifest not found at {manifest_path}", file=sys.stderr)
        print("Run 'verify_aikeep.py generate' first to create the manifest.", file=sys.stderr)
        return False

    saved_blocks = load_manifest(manifest_path)
    current_blocks = scan_tex_files(root_dir)

    # Create lookup dictionaries (include block_type in key for uniqueness)
    saved_lookup = {(b.file, b.hash, b.block_type): b for b in saved_blocks}
    current_lookup = {(b.file, b.hash, b.block_type): b for b in current_blocks}

    errors = []
    warnings = []

    # Check for modified or removed blocks
    for key, saved in saved_lookup.items():
        if key not in current_lookup:
            # Block was modified or removed - check by file and approximate line
            found_in_file = [b for b in current_blocks if b.file == saved.file and b.block_type == saved.block_type]
            type_label = f"\\{saved.block_type}"
            if not found_in_file:
                errors.append(f"REMOVED [{type_label}]: {saved.file}:{saved.line}")
                errors.append(f"  Content: {saved.content[:60]}{'...' if len(saved.content) > 60 else ''}")
            else:
                # Check if content at similar location changed
                errors.append(f"MODIFIED [{type_label}]: {saved.file}:{saved.line}")
                errors.append(f"  Original: {saved.content[:60]}{'...' if len(saved.content) > 60 else ''}")
                # Try to find the modified version
                for current in found_in_file:
                    if abs(current.line - saved.line) <= 5:
                        errors.append(f"  Current:  {current.content[:60]}{'...' if len(current.content) > 60 else ''}")
                        break

    # Check for new blocks (not an error, but informational)
    for key, current in current_lookup.items():
        if key not in saved_lookup:
            type_label = f"\\{current.block_type}"
            warnings.append(f"NEW [{type_label}]: {current.file}:{current.line}")
            warnings.append(f"  Content: {current.content[:60]}{'...' if len(current.content) > 60 else ''}")

    # Check ordering of \aianchor blocks (they must maintain their relative order)
    order_errors = verify_anchor_order(saved_blocks, current_blocks)
    errors.extend(order_errors)

    # Print results
    if errors:
        print("=" * 70)
        print("VERIFICATION FAILED: Protected content has been modified!")
        print("=" * 70)
        for error in errors:
            print(f"  {error}")
        print()

    if warnings:
        print("-" * 70)
        print("New protected blocks (not in manifest):")
        print("-" * 70)
        for warning in warnings:
            print(f"  {warning}")
        print()

    if not errors and not warnings:
        print(f"✓ Verification passed: {len(saved_blocks)} protected block(s) unchanged")
        return True
    elif not errors:
        print(f"✓ Verification passed with {len(warnings)//2} new block(s)")
        print("  Run 'verify_aikeep.py generate' to update the manifest")
        return True
    else:
        print(f"✗ Verification failed")
        return False


def verify_anchor_order(saved_blocks: list[ProtectedBlock], current_blocks: list[ProtectedBlock]) -> list[str]:
    """
    Verify that \aianchor blocks maintain their relative order.

    Args:
        saved_blocks: Blocks from the manifest
        current_blocks: Current blocks from files

    Returns:
        List of error messages if order violations are found
    """
    errors = []

    # Get only aianchor blocks, grouped by file
    saved_anchors_by_file: dict[str, list[ProtectedBlock]] = {}
    current_anchors_by_file: dict[str, list[ProtectedBlock]] = {}

    for block in saved_blocks:
        if block.block_type == 'aianchor':
            if block.file not in saved_anchors_by_file:
                saved_anchors_by_file[block.file] = []
            saved_anchors_by_file[block.file].append(block)

    for block in current_blocks:
        if block.block_type == 'aianchor':
            if block.file not in current_anchors_by_file:
                current_anchors_by_file[block.file] = []
            current_anchors_by_file[block.file].append(block)

    # Check order within each file
    for filepath in saved_anchors_by_file:
        if filepath not in current_anchors_by_file:
            continue  # File missing anchors is handled elsewhere

        saved_anchors = saved_anchors_by_file[filepath]
        current_anchors = current_anchors_by_file[filepath]

        # Build order map: hash -> position in saved
        saved_order = {b.hash: i for i, b in enumerate(saved_anchors)}

        # Check if current anchors that exist in saved maintain relative order
        current_hashes_in_saved = [b.hash for b in current_anchors if b.hash in saved_order]
        expected_positions = [saved_order[h] for h in current_hashes_in_saved]

        # Check if positions are monotonically increasing (order preserved)
        for i in range(1, len(expected_positions)):
            if expected_positions[i] < expected_positions[i-1]:
                # Order violation detected
                hash_a = current_hashes_in_saved[i-1]
                hash_b = current_hashes_in_saved[i]

                # Find the actual blocks for better error messages
                anchor_a = next(b for b in saved_anchors if b.hash == hash_a)
                anchor_b = next(b for b in saved_anchors if b.hash == hash_b)

                errors.append(f"ORDER VIOLATION [\\aianchor]: {filepath}")
                errors.append(f"  Anchor at original line {anchor_a.line} now appears AFTER anchor from line {anchor_b.line}")
                errors.append(f"  First:  {anchor_a.content[:50]}{'...' if len(anchor_a.content) > 50 else ''}")
                errors.append(f"  Second: {anchor_b.content[:50]}{'...' if len(anchor_b.content) > 50 else ''}")
                break  # Report first violation per file

    return errors


def list_blocks(root_dir: Path) -> None:
    """
    List all protected blocks in the project.

    Args:
        root_dir: Root directory to scan
    """
    blocks = scan_tex_files(root_dir)

    if not blocks:
        print("No protected blocks found.")
        return

    aikeep_count = sum(1 for b in blocks if b.block_type == 'aikeep')
    aianchor_count = sum(1 for b in blocks if b.block_type == 'aianchor')
    print(f"Found {len(blocks)} protected block(s) ({aikeep_count} \\aikeep, {aianchor_count} \\aianchor):\n")

    current_file = None
    for block in blocks:
        if block.file != current_file:
            current_file = block.file
            print(f"[{block.file}]")

        # Format content for display (truncate if needed)
        content_display = block.content.replace('\n', '\\n')
        if len(content_display) > 60:
            content_display = content_display[:57] + "..."

        type_label = f"\\{block.block_type}"
        print(f"  Line {block.line:3d} [{type_label:10s}]: {content_display}")
        print(f"                          Hash: {block.hash}")
    print()


def show_diff(root_dir: Path, manifest_path: Path) -> None:
    """
    Show differences between current state and manifest.

    Args:
        root_dir: Root directory to scan
        manifest_path: Path to the manifest file
    """
    if not manifest_path.exists():
        print(f"Error: Manifest not found at {manifest_path}", file=sys.stderr)
        print("Run 'verify_aikeep.py generate' first.", file=sys.stderr)
        return

    saved_blocks = load_manifest(manifest_path)
    current_blocks = scan_tex_files(root_dir)

    saved_by_file_line = {(b.file, b.line): b for b in saved_blocks}
    current_by_file_line = {(b.file, b.line): b for b in current_blocks}

    changes = []

    # Find modifications
    for key in saved_by_file_line:
        saved = saved_by_file_line[key]
        if key in current_by_file_line:
            current = current_by_file_line[key]
            if saved.hash != current.hash:
                changes.append(('modified', saved, current))
        else:
            changes.append(('removed', saved, None))

    # Find additions
    for key in current_by_file_line:
        if key not in saved_by_file_line:
            changes.append(('added', None, current_by_file_line[key]))

    if not changes:
        print("No changes detected.")
        return

    print(f"Found {len(changes)} change(s):\n")

    for change_type, old, new in changes:
        if change_type == 'modified':
            print(f"MODIFIED: {old.file}:{old.line}")
            print(f"  - {old.content}")
            print(f"  + {new.content}")
        elif change_type == 'removed':
            print(f"REMOVED: {old.file}:{old.line}")
            print(f"  - {old.content}")
        elif change_type == 'added':
            print(f"ADDED: {new.file}:{new.line}")
            print(f"  + {new.content}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Verify \\aikeep{} and \\aianchor{} protected content in LaTeX files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  generate  Create or update the manifest file
  verify    Check current files against the manifest
  list      List all protected blocks in the project
  diff      Show changes since manifest was created

Examples:
  %(prog)s generate        # Create .aikeep-manifest.json
  %(prog)s verify          # Verify no protected content was modified
  %(prog)s list            # Show all \\aikeep{} and \\aianchor{} blocks
  %(prog)s diff            # Show what changed
"""
    )

    parser.add_argument(
        'command',
        choices=['generate', 'verify', 'list', 'diff'],
        help='Command to execute'
    )

    parser.add_argument(
        '--manifest', '-m',
        type=Path,
        default=Path('.aikeep-manifest.json'),
        help='Path to manifest file (default: .aikeep-manifest.json)'
    )

    parser.add_argument(
        '--root', '-r',
        type=Path,
        default=Path('.'),
        help='Root directory to scan (default: current directory)'
    )

    args = parser.parse_args()

    # Resolve paths
    root_dir = args.root.resolve()
    manifest_path = args.manifest
    if not manifest_path.is_absolute():
        manifest_path = root_dir / manifest_path

    if args.command == 'generate':
        generate_manifest(root_dir, manifest_path)
    elif args.command == 'verify':
        success = verify_manifest(root_dir, manifest_path)
        sys.exit(0 if success else 1)
    elif args.command == 'list':
        list_blocks(root_dir)
    elif args.command == 'diff':
        show_diff(root_dir, manifest_path)


if __name__ == '__main__':
    main()
