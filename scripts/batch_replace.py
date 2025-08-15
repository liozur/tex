"""Batch regex replacement script with regex-based rules/target files selection.

Features:
    - Regex select rules files (sorted by file name).
    - Regex select target files.
    - Apply rules from all matched rules files to all matched target files.
    - Default: backup target before modifying (filename + ".backup").
    - Option: --overwrite / -o  to skip creating backups.
    - Option: --dry-run / -d to preview changes without modifying files.

Rules file format:
    Each rule consists of three lines:
        1. Regex pattern
        2. Replacement string
        3. Blank line (separator)
"""

import re
import os
import shutil
import argparse
from typing import List, Tuple


def load_rules_from_file(rules_path: str) -> List[Tuple[str, str]]:
    """Load regex-replacement rules from a single rules file."""
    if not os.path.isfile(rules_path):
        raise FileNotFoundError(f"Rules file not found: {rules_path}")
    rules = []
    with open(rules_path, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f]
        for i in range(0, len(lines), 3):
            if i + 1 < len(lines):
                pattern = lines[i]
                replacement = lines[i + 1]
                if pattern:
                    rules.append((pattern, replacement))
    return rules


def apply_rules_to_text(
    text: str, rules: List[Tuple[str, str]]
) -> Tuple[str, List[int]]:
    """Apply all regex-replacement rules to the given text."""
    counts = []
    for pattern, replacement in rules:
        count = len(re.findall(pattern, text, flags=re.MULTILINE))
        text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
        counts.append(count)
    return text, counts


def backup_file(file_path: str) -> None:
    """Create a backup of the given file in the same directory with '.backup' suffix."""
    backup_path = f"{file_path}.backup"
    shutil.copy2(file_path, backup_path)
    print(f"   Backup created: {backup_path}")


def process_file(
    rules: List[Tuple[str, str]], file_path: str, overwrite: bool, dry_run: bool
) -> bool:
    """Apply rules to a file with optional backup or dry-run."""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    new_text, counts = apply_rules_to_text(text, rules)

    print(f"\n== Processing target file: {file_path}")
    for idx, ((pattern, replacement), cnt) in enumerate(zip(rules, counts), 1):
        print(f"   Rule {idx}: {pattern} -> {replacement} (Replaced {cnt})")

    if new_text != text:
        if dry_run:
            print("   Dry-run mode: no changes written.")
            return True
        if not overwrite:
            backup_file(file_path)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_text)
        print("   File updated.")
        return True
    print("   No changes.")
    return False


def iter_files_with_regex(path_regex: str) -> List[str]:
    """Find files whose relative paths match the given regex."""
    compiled = re.compile(path_regex)
    matched_files = []
    root = os.getcwd()
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            full_path = os.path.join(dirpath, fn)
            rel_path = os.path.relpath(full_path, root).replace(os.sep, "/")
            if compiled.search(rel_path):
                matched_files.append(full_path)
    return matched_files


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch regex replace tool (rules regex + target regex)"
    )
    parser.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help="Overwrite target files without creating backups.",
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying or backing up files.",
    )
    parser.add_argument(
        "rules_regex",
        help="Regex to match rules file paths (relative to current dir). "
        "Matched files will be sorted by file name before execution.",
    )
    parser.add_argument(
        "target_regex",
        help="Regex to match target file paths (relative to current dir).",
    )
    args = parser.parse_args()

    # Locate rules files
    try:
        rules_files = iter_files_with_regex(args.rules_regex)
    except re.error as e:
        print(f"Invalid rules regex: {e}")
        raise SystemExit(1)
    if not rules_files:
        print("No rules files matched the provided regex.")
        raise SystemExit(2)
    rules_files.sort(key=lambda p: os.path.basename(p))
    print(f"Found {len(rules_files)} rules files (sorted by name):")
    for rf in rules_files:
        print(f"  {rf}")

    # Locate target files
    try:
        target_files = iter_files_with_regex(args.target_regex)
    except re.error as e:
        print(f"Invalid target regex: {e}")
        raise SystemExit(1)
    if not target_files:
        print("No target files matched the provided regex.")
        raise SystemExit(2)
    print(f"Found {len(target_files)} target files.")

    # Apply each rules file
    total_changed = 0
    for rules_path in rules_files:
        rules = load_rules_from_file(rules_path)
        print(f"\n=== Executing rules from: {rules_path} ({len(rules)} rules) ===")
        for target_file in target_files:
            if process_file(rules, target_file, args.overwrite, args.dry_run):
                total_changed += 1

    print(
        f"\nDone. Target files processed: {len(target_files)}. "
        f"Total file modifications: {total_changed}."
        f"{' (dry-run)' if args.dry_run else ''}"
    )


if __name__ == "__main__":
    main()
