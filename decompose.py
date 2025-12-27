#!/usr/bin/env python3
"""
HW3 (Version 2.0.0) - Super simple 3NF / BCNF task.

You only need to fill in two functions below:
- solve_3nf(...)
- solve_bcnf(...)
We already read the JSON file for you and print the result.
No fancy Python features, just lists and dicts.
"""
import json
import sys
from pathlib import Path

# Keep this version as-is
ASSIGNMENT_VERSION = (2, 0, 0)  # v2.0.0


def _normalize_fds(functional_dependencies):
    """Convert raw FD dicts to internal form: list of {'left': set, 'right': str}."""
    fds = []
    for fd in functional_dependencies:
        left = set(fd["left"])
        # right always has exactly one attribute
        right = fd["right"][0] 
        fds.append({"left": left, "right": right})
    return fds


def _closure(attrs, fds):
    """
    Compute attribute closure of a set of attributes `attrs`
    with respect to functional dependencies `fds`.
    """
    closure = set(attrs)
    changed = True
    while changed:
        changed = False
        for fd in fds:
            if fd["left"].issubset(closure) and fd["right"] not in closure:
                closure.add(fd["right"])
                changed = True
    return closure


def _minimal_cover(fds):
    """
    Compute a minimal cover of the functional dependencies.

    Here we assume:
      - every FD already has a single attribute on the right (given by the spec).
    We only remove *redundant* FDs, and we do NOT try to remove
    attributes from the left-hand sides (that was causing issues).
    """
    # Work on a copy with sets for the left side
    fds = [{"left": set(fd["left"]), "right": fd["right"]} for fd in fds]

    # Remove redundant FDs
    i = 0
    while i < len(fds):
        fd = fds[i]
        other_fds = fds[:i] + fds[i + 1 :]
        # if fd.right is already implied by fd.left using the other FDs, fd is redundant
        if fd["right"] in _closure(fd["left"], other_fds):
            fds.pop(i)
        else:
            i += 1

    return fds



def _find_key(attributes, fds):
    """
    Find one (not necessarily all) minimal key for the relation.
    """
    attrs_set = set(attributes)
    # Attributes that never appear on the right must be in every key
    right_attrs = {fd["right"] for fd in fds}
    key = attrs_set - right_attrs
    if not key:
        # Fallback: start from an arbitrary attribute
        key = {next(iter(attrs_set))}

    # Make it a superkey
    while _closure(key, fds) != attrs_set:
        remaining = attrs_set - _closure(key, fds)
        key.add(next(iter(remaining)))

    # Make it minimal
    for a in list(key):
        if _closure(key - {a}, fds) == attrs_set:
            key.remove(a)

    return key


def solve_3nf(relation_name, attributes, functional_dependencies):
    """
    Return the 3NF decomposition as a list of relations (each a list of attributes).
    """
    attrs_set = set(attributes)
    fds = _normalize_fds(functional_dependencies)
    cover = _minimal_cover(fds)

    # Step 1: create a relation for each FD in the minimal cover
    relation_sets = []
    seen = set()
    for fd in cover:
        rel = fd["left"].copy()
        rel.add(fd["right"])
        rel &= attrs_set  # just in case
        frel = frozenset(rel)
        if frel not in seen:
            seen.add(frel)
            relation_sets.append(rel)

    # Step 2: ensure a key of the original relation is contained
    key = _find_key(attributes, cover)
    if not any(key.issubset(rel) for rel in relation_sets):
        relation_sets.append(set(key))

    # Step 3: remove redundant relations (those contained in another)
    i = 0
    while i < len(relation_sets):
        rel_i = relation_sets[i]
        redundant = False
        for j, rel_j in enumerate(relation_sets):
            if i != j and rel_i.issubset(rel_j):
                redundant = True
                break
        if redundant:
            relation_sets.pop(i)
        else:
            i += 1

    # Convert to the required output format: list of lists, sorted for determinism
    result = [sorted(list(rel)) for rel in relation_sets]
    result.sort()
    return result


def _bcnf_decompose(attrs_set, fds):
    """
    Recursively decompose attrs_set into BCNF using fds.
    Returns a list of sets of attributes.
    """
    # Restrict FDs to this relation
    relevant_fds = []
    for fd in fds:
        if fd["left"].issubset(attrs_set) and fd["right"] in attrs_set:
            relevant_fds.append({"left": set(fd["left"]), "right": fd["right"]})

    # Find an FD that violates BCNF
    violating_fd = None
    for fd in relevant_fds:
        if not _closure(fd["left"], relevant_fds).issuperset(attrs_set):
            violating_fd = fd
            break

    if violating_fd is None:
        # This relation is already in BCNF
        return [attrs_set]

    X = violating_fd["left"]
    X_plus = _closure(X, relevant_fds) & attrs_set

    # R1 = X+
    R1 = X_plus
    # R2 = R - (X+ - X)
    R2 = attrs_set - (X_plus - X)

    res1 = _bcnf_decompose(R1, fds)
    res2 = _bcnf_decompose(R2, fds)
    return res1 + res2


def solve_bcnf(relation_name, attributes, functional_dependencies):
    """
    Return the BCNF decomposition as a list of relations (each a list of attributes).
    """
    attrs_set = set(attributes)
    fds = _normalize_fds(functional_dependencies)

    relation_sets = _bcnf_decompose(attrs_set, fds)

    # Remove duplicates if any
    unique = []
    for rel in relation_sets:
        if rel not in unique:
            unique.append(rel)

    result = [sorted(list(rel)) for rel in unique]
    result.sort()
    return result


def _read_input_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    relation_name = data.get("relationName", "R")
    attributes = data.get("attributes", [])
    fds = data.get("functionalDependencies", [])
    return relation_name, attributes, fds


def _validate_input(attributes, fds):
    if not attributes:
        raise ValueError("attributes must be a non-empty list")
    for i, fd in enumerate(fds):
        if "left" not in fd or "right" not in fd:
            raise ValueError(f"FD #{i} must have 'left' and 'right'")
        if not fd["left"] or not fd["right"]:
            raise ValueError(f"FD #{i} must have non-empty left and right")
        if len(fd["right"]) != 1:
            raise ValueError(f"FD #{i} right side must have exactly one attribute")
        # Basic attribute name check
        for a in fd["left"] + fd["right"]:
            if a not in attributes:
                raise ValueError(f"FD #{i} contains unknown attribute '{a}'")


def main():
    # Usage: python3 decompose_v2.py path/to/test.json
    if len(sys.argv) != 2:
        print("Usage: python3 decompose_v2.py path/to/test.json")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        sys.exit(1)

    relation_name, attributes, fds = _read_input_json(str(input_path))
    _validate_input(attributes, fds)

    # Students implement both functions
    result = {
        "3nf": solve_3nf(relation_name, attributes, fds),
        "bcnf": solve_bcnf(relation_name, attributes, fds),
    }

    # We just print the result as JSON
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
