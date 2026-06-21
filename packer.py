#!/usr/bin/env python3
"""
Halo Resource Pack Packer
=========================
Scans an 'input/' folder for halo definition JSONs and PNG textures,
then interactively lets you choose how to pack them:

  [1] Individual  — one pack per halo definition
  [2] By namespace — one pack per namespace (all halos under it grouped)
  [3] Combined     — all definitions in a single pack
  [4] Pick         — select specific definitions to pack individually
  [5] Custom       — pick specific definitions, then choose per-namespace or individual

Output is written to 'output/' as .zip files.

Usage:
    python packer.py
"""

import json
import os
import sys
import zipfile
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(SCRIPT_DIR, "input")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
INDIV_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "Individual")
NS_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "Namespace")

PACK_FORMAT = 15  # Minecraft 1.20.x


# ---------------------------------------------------------------------------
# File scanning
# ---------------------------------------------------------------------------

def collect_files():
    """Scan input/ and separate JSON definitions from PNG textures."""
    if not os.path.isdir(INPUT_DIR):
        print(f"[ERROR] Input directory not found: {INPUT_DIR}")
        sys.exit(1)

    all_files = os.listdir(INPUT_DIR)
    json_files = sorted(f for f in all_files if f.lower().endswith(".json"))
    png_files = sorted(f for f in all_files if f.lower().endswith(".png"))

    print(f"[INFO] Found {len(json_files)} JSON file(s), {len(png_files)} PNG file(s) in input/")
    return json_files, png_files


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

def extract_texture_refs(json_path):
    """
    Parse a halo definition JSON and extract all texture references.
    Returns (id_namespace, id_name, set of texture filenames) or (None, None, set()) on failure.
    """
    full_path = os.path.join(INPUT_DIR, json_path)
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[WARN] Failed to parse {json_path}: {e}")
        return None, None, set()

    raw_id = data.get("id")
    if not raw_id or ":" not in raw_id:
        print(f"[WARN] {json_path}: missing or malformed 'id' field, skipping")
        return None, None, set()

    id_ns, id_name = raw_id.split(":", 1)
    textures = set()

    def add_texture(tex_path):
        if tex_path and ":" in tex_path:
            filename = os.path.basename(tex_path.split(":", 1)[1])
            textures.add(filename)

    # New format: layers[].primitive.texture, layers[].primitive.glow.texture
    for layer in data.get("layers", []):
        prim = layer.get("primitive", {})
        add_texture(prim.get("texture"))
        glow = prim.get("glow", {})
        if isinstance(glow, dict):
            add_texture(glow.get("texture"))

    # Legacy format: shape.texture or shape.layers[].texture
    shape = data.get("shape")
    if shape:
        add_texture(shape.get("texture"))
        for sl in shape.get("layers", []):
            add_texture(sl.get("texture"))

    return id_ns, id_name, textures


# ---------------------------------------------------------------------------
# Build record list
# ---------------------------------------------------------------------------

def build_records(json_files, png_set):
    """
    Parse each JSON and build a record dict.
    Returns list of records: {json, id_ns, id_name, pngs}.
    Also detects naming collisions.
    """
    records = []
    name_counts = defaultdict(list)

    for jf in json_files:
        id_ns, id_name, tex_refs = extract_texture_refs(jf)
        if id_ns is None:
            continue

        matched_pngs = set()
        for tex in tex_refs:
            if tex in png_set:
                matched_pngs.add(tex)
            else:
                print(f"[WARN] {jf}: texture '{tex}' not found in input/")

        name_counts[id_name].append(id_ns)
        records.append({
            "json": jf,
            "id_ns": id_ns,
            "id_name": id_name,
            "pngs": matched_pngs,
        })

    # Detect collisions
    collisions = {name for name, nss in name_counts.items() if len(set(nss)) > 1}
    return records, collisions


# ---------------------------------------------------------------------------
# Zip writer
# ---------------------------------------------------------------------------

def make_pack_mcmeta(description):
    meta = {
        "pack": {
            "pack_format": PACK_FORMAT,
            "description": description,
        }
    }
    return json.dumps(meta, indent=2, ensure_ascii=False)


def write_zip(zip_path, records, description):
    """
    Write a resource pack zip containing the given records' JSONs and PNGs.
    `records` is a list of record dicts.
    """
    ns_jsons = defaultdict(list)
    for rec in records:
        ns_jsons[rec["id_ns"]].append(rec["json"])

    # png -> set of namespaces
    png_ns_map = defaultdict(set)
    for rec in records:
        for png in rec["pngs"]:
            png_ns_map[png].add(rec["id_ns"])

    total_files = 1 + sum(len(v) for v in ns_jsons.values()) + len(png_ns_map)
    print(f"  Creating: {os.path.basename(zip_path)} ({total_files} files)")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("pack.mcmeta", make_pack_mcmeta(description))

        for ns, jfiles in ns_jsons.items():
            for jf in jfiles:
                src = os.path.join(INPUT_DIR, jf)
                dst = f"assets/{ns}/halo_definitions/{jf}"
                zf.write(src, dst)

        for png, namespaces in png_ns_map.items():
            src = os.path.join(INPUT_DIR, png)
            if not os.path.exists(src):
                print(f"[WARN] Texture file missing: {png}")
                continue
            for ns in namespaces:
                dst = f"assets/{ns}/textures/halo/{png}"
                zf.write(src, dst)


# ---------------------------------------------------------------------------
# Naming helpers
# ---------------------------------------------------------------------------

def make_zip_name(rec, collisions):
    """Generate zip filename for an individual record."""
    base = f"{rec['id_ns']}_{rec['id_name']}" if rec["id_name"] in collisions else rec["id_name"]
    return base[0].upper() + base[1:]


def make_indiv_desc(rec):
    """Description for an individual halo pack."""
    return f"{rec['id_name']}'s halo pack"


def make_namespace_desc(ns, records):
    """Description for a namespace-grouped pack."""
    names = ", ".join(r["id_name"] for r in records)
    return f"{ns} halo pack ({names})"


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def print_summary(records, collisions):
    """Print a summary of found definitions grouped by namespace."""
    by_ns = defaultdict(list)
    for rec in records:
        by_ns[rec["id_ns"]].append(rec)

    print("\n" + "=" * 60)
    print("  Definitions found")
    print("=" * 60)
    for ns in sorted(by_ns.keys()):
        defs = by_ns[ns]
        print(f"\n  [{ns}]  ({len(defs)} definition(s))")
        for i, rec in enumerate(defs):
            png_info = ", ".join(sorted(rec["pngs"])) if rec["pngs"] else "(no textures)"
            marker = " ⚠ name collision" if rec["id_name"] in collisions else ""
            print(f"    {i+1}. {rec['id_name']}  -> {png_info}{marker}")
    print()


def print_indexed_list(records, collisions):
    """Print a flat numbered list of all definitions."""
    for i, rec in enumerate(records):
        png_info = ", ".join(sorted(rec["pngs"])) if rec["pngs"] else "(no textures)"
        marker = " ⚠ name collision" if rec["id_name"] in collisions else ""
        print(f"  [{i+1}] {rec['id_ns']}:{rec['id_name']}  -> {png_info}{marker}")


def pick_records(records, collisions, prompt="Select definitions"):
    """Interactive multi-pick from the record list. Returns list of selected records."""
    print(f"\n{'-' * 40}")
    print(f"  {prompt}")
    print(f"{'-' * 40}")
    print_indexed_list(records, collisions)
    print(f"  [a] Select all  [q] Done")
    print()

    selected = set()
    while True:
        choice = input("  Enter number(s) or command: ").strip().lower()
        if choice == "q":
            break
        if choice == "a":
            selected = set(range(len(records)))
            break
        # Support comma/space-separated numbers and ranges like "1-3"
        parts = choice.replace(",", " ").split()
        for p in parts:
            if "-" in p:
                try:
                    a, b = p.split("-", 1)
                    for n in range(int(a) - 1, int(b)):
                        if 0 <= n < len(records):
                            selected.add(n)
                except ValueError:
                    print(f"  [WARN] Ignoring bad range: {p}")
            else:
                try:
                    n = int(p) - 1
                    if 0 <= n < len(records):
                        selected.add(n)
                except ValueError:
                    print(f"  [WARN] Ignoring: {p}")

    return [records[i] for i in sorted(selected)]


# ---------------------------------------------------------------------------
# Packing modes
# ---------------------------------------------------------------------------

def run_individual(records, collisions):
    """One pack per halo definition."""
    os.makedirs(INDIV_OUTPUT_DIR, exist_ok=True)
    print(f"\n[Mode] Individual packs ({len(records)} pack(s))")
    for rec in records:
        zip_name = make_zip_name(rec, collisions) + ".zip"
        zip_path = os.path.join(INDIV_OUTPUT_DIR, zip_name)
        write_zip(zip_path, [rec], make_indiv_desc(rec))
        print(f"    -> Individual/{zip_name}")


def run_by_namespace(records, collisions):
    """One pack per namespace."""
    os.makedirs(NS_OUTPUT_DIR, exist_ok=True)
    by_ns = defaultdict(list)
    for rec in records:
        by_ns[rec["id_ns"]].append(rec)

    print(f"\n[Mode] By namespace ({len(by_ns)} pack(s))")
    for ns in sorted(by_ns.keys()):
        group = by_ns[ns]
        zip_name = f"{ns[0].upper() + ns[1:]}_halos.zip"
        zip_path = os.path.join(NS_OUTPUT_DIR, zip_name)
        write_zip(zip_path, group, make_namespace_desc(ns, group))
        print(f"    -> Namespace/{zip_name}")


def run_combined(records, collisions):
    """All definitions in one pack."""
    print(f"\n[Mode] Combined pack ({len(records)} definition(s))")
    zip_name = "All the halo pack.zip"
    zip_path = os.path.join(OUTPUT_DIR, zip_name)
    write_zip(zip_path, records, "all the halo inside")
    print(f"    -> {zip_name}")


def run_pick(records, collisions):
    """Let the user pick specific definitions, then pack them individually."""
    os.makedirs(INDIV_OUTPUT_DIR, exist_ok=True)
    chosen = pick_records(records, collisions, "Pick definitions to pack individually")
    if not chosen:
        print("[WARN] No definitions selected, skipping.")
        return
    print(f"\n[Mode] Individual packs for {len(chosen)} selected definition(s)")
    for rec in chosen:
        zip_name = make_zip_name(rec, collisions) + ".zip"
        zip_path = os.path.join(INDIV_OUTPUT_DIR, zip_name)
        write_zip(zip_path, [rec], make_indiv_desc(rec))
        print(f"    -> Individual/{zip_name}")


def run_custom(records, collisions):
    """Pick specific definitions, then choose per-namespace or individual packing."""
    chosen = pick_records(records, collisions, "Pick definitions to include")
    if not chosen:
        print("[WARN] No definitions selected, skipping.")
        return

    print(f"\n  Pack these {len(chosen)} definition(s) as:")
    print("    [1] Individual  — one pack each")
    print("    [2] By namespace — group by namespace")
    print("    [3] Combined     — single pack")

    mode = input("  Choice (1/2/3): ").strip()
    if mode == "2":
        os.makedirs(NS_OUTPUT_DIR, exist_ok=True)
        run_by_namespace(chosen, collisions)
    elif mode == "3":
        run_combined(chosen, collisions)
    else:
        os.makedirs(INDIV_OUTPUT_DIR, exist_ok=True)
        run_individual(chosen, collisions)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(INDIV_OUTPUT_DIR, exist_ok=True)
    os.makedirs(NS_OUTPUT_DIR, exist_ok=True)

    json_files, png_files = collect_files()
    if not json_files:
        print("[WARN] No JSON files found in input/. Nothing to pack.")
        return

    png_set = set(png_files)
    records, collisions = build_records(json_files, png_set)

    if not records:
        print("[WARN] No valid halo definitions found.")
        return

    print_summary(records, collisions)

    # Menu loop
    while True:
        print("-" * 40)
        print("  Packing options:")
        print("    [1] Individual   — one pack per halo definition")
        print("    [2] By namespace  — one pack per namespace")
        print("    [3] Combined      — all definitions in a single pack")
        print("    [4] Pick          — select specific definitions → individual packs")
        print("    [5] Custom        — pick definitions, then choose grouping")
        print("    [q] Quit")
        print()

        choice = input("  Choice: ").strip().lower()

        if choice == "1":
            run_individual(records, collisions)
        elif choice == "2":
            run_by_namespace(records, collisions)
        elif choice == "3":
            run_combined(records, collisions)
        elif choice == "4":
            run_pick(records, collisions)
        elif choice == "5":
            run_custom(records, collisions)
        elif choice == "q":
            print("\nBye!")
            break
        else:
            print(f"[WARN] Unknown option: '{choice}'")

        print(f"\n[DONE] Output written to {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()
