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


def normalize_content(content: str) -> str:
    """
    Normalize protected content for comparison.

    Runs of whitespace collapse to a single space and the ends are stripped,
    because TeX already treats them that way: re-wrapping a paragraph changes
    the source bytes but not one glyph of the output. Hashing the raw bytes
    would fail the build every time an editor reflowed a line, which trains
    people to ignore the check.
    """
    return ' '.join(content.split())


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
        """Create a ProtectedBlock with a hash over the normalized content."""
        normalized = normalize_content(content)
        content_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]
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
        "version": 3,
        "description": (
            "AI-protected content manifest for \\aikeep{} and \\aianchor{} blocks. "
            "Hashes are computed over whitespace-normalized content."
        ),
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

    # Handle v1 (no block_type), v2 (block_type, raw-byte hashes) and v3
    # manifests. The stored hash is deliberately ignored and recomputed from
    # the stored content, so a manifest written by an older version keeps
    # working under the current normalization rules without regeneration.
    blocks = []
    for b in data["blocks"]:
        blocks.append(ProtectedBlock.from_content(
            file=b["file"],
            line=b["line"],
            content=b["content"],
            block_type=b.get("block_type", "aikeep"),
        ))
    return blocks


def diff_blocks(
    saved_blocks: list[ProtectedBlock],
    current_blocks: list[ProtectedBlock],
) -> dict[str, list]:
    """
    Compute a block-level diff between manifest and current state.

    Blocks are identified by their content hash within a (file, block_type)
    group, never by line number -- inserting an unrelated paragraph shifts every
    line below it without changing any protected content.

    Returns a dict with keys:
        'moved'    -> list of (saved, current) whose content matches but line differs
        'modified' -> list of (saved, current) pairs
        'removed'  -> list of saved blocks with no counterpart
        'added'    -> list of current blocks with no counterpart
    """
    def group(blocks: list[ProtectedBlock]) -> dict[tuple[str, str], list[ProtectedBlock]]:
        out: dict[tuple[str, str], list[ProtectedBlock]] = {}
        for b in blocks:
            out.setdefault((b.file, b.block_type), []).append(b)
        return out

    saved_groups = group(saved_blocks)
    current_groups = group(current_blocks)

    result: dict[str, list] = {'moved': [], 'modified': [], 'removed': [], 'added': []}

    for key in sorted(set(saved_groups) | set(current_groups)):
        saved_group = saved_groups.get(key, [])
        current_group = current_groups.get(key, [])

        # Match blocks whose content is byte-identical, in document order.
        # A block that still exists somewhere in the file is never "removed",
        # even if it moved -- reordering is reported by verify_anchor_order.
        remaining_current = list(current_group)
        saved_only: list[ProtectedBlock] = []
        for saved in saved_group:
            match = next((c for c in remaining_current if c.hash == saved.hash), None)
            if match is None:
                saved_only.append(saved)
            else:
                remaining_current.remove(match)
                if match.line != saved.line:
                    result['moved'].append((saved, match))

        # Whatever is left on both sides is an edit; pair in document order so
        # the reported "Original -> Current" is the block that actually changed.
        for saved, current in zip(saved_only, remaining_current):
            result['modified'].append((saved, current))
        result['removed'].extend(saved_only[len(remaining_current):])
        result['added'].extend(remaining_current[len(saved_only):])

    return result


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

    delta = diff_blocks(saved_blocks, current_blocks)

    errors = []
    warnings = []

    def excerpt(block: ProtectedBlock, limit: int = 60) -> str:
        text = block.content.replace('\n', ' ')
        return f"{text[:limit]}{'...' if len(text) > limit else ''}"

    for saved, current in delta['modified']:
        errors.append(f"MODIFIED [\\{saved.block_type}]: {saved.file}:{saved.line}")
        errors.append(f"  Original: {excerpt(saved)}")
        errors.append(f"  Current:  {excerpt(current)}")

    for saved in delta['removed']:
        errors.append(f"REMOVED [\\{saved.block_type}]: {saved.file}:{saved.line}")
        errors.append(f"  Content: {excerpt(saved)}")

    for current in delta['added']:
        warnings.append(f"NEW [\\{current.block_type}]: {current.file}:{current.line}")
        warnings.append(f"  Content: {excerpt(current)}")

    # Check ordering of \aianchor blocks (they must maintain their relative order)
    errors.extend(verify_anchor_order(saved_blocks, current_blocks))

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
        print(f"\u2713 Verification passed: {len(saved_blocks)} protected block(s) unchanged")
        return True
    elif not errors:
        print(f"\u2713 Verification passed with {len(delta['added'])} new block(s)")
        print("  Run 'verify_aikeep.py generate' to update the manifest")
        return True
    else:
        print(f"\u2717 Verification failed")
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

    delta = diff_blocks(saved_blocks, current_blocks)

    total = sum(len(delta[k]) for k in ('modified', 'removed', 'added'))
    if total == 0 and not delta['moved']:
        print("No changes detected.")
        return

    if total == 0:
        print(f"No content changes ({len(delta['moved'])} block(s) shifted position):\n")
    else:
        print(f"Found {total} change(s):\n")

    for saved, current in delta['modified']:
        print(f"MODIFIED [\\{saved.block_type}]: {saved.file}:{saved.line}")
        print(f"  - {saved.content}")
        print(f"  + {current.content}")
        print()

    for saved in delta['removed']:
        print(f"REMOVED [\\{saved.block_type}]: {saved.file}:{saved.line}")
        print(f"  - {saved.content}")
        print()

    for current in delta['added']:
        print(f"ADDED [\\{current.block_type}]: {current.file}:{current.line}")
        print(f"  + {current.content}")
        print()

    for saved, current in delta['moved']:
        print(f"MOVED [\\{saved.block_type}]: {saved.file}:{saved.line} -> {current.line} (content unchanged)")
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
