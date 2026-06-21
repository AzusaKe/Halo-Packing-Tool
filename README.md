# Halo Resource Pack Packer

Pack bare JSON definition files and PNG textures into ready-to-use Minecraft resource packs (`.zip`), in a single step.

## Usage

1. Place your halo definition files (`.json`) and texture files (`.png`) into the `input/` folder
2. Run the script:

```bash
python3 packer.py
```

3. The script scans all files in `input/`, displays a summary of found definitions and their referenced textures
4. Choose a packing mode from the interactive menu — output is written to `output/`

## Packing Modes

| Option | Description |
|------|------|
| `[1] Individual` | One resource pack per halo definition |
| `[2] By namespace` | Group by namespace — all halos under one namespace merged into a single pack |
| `[3] Combined` | All halo definitions merged into a single pack |
| `[4] Pick` | Manually select specific definitions, each packed individually |
| `[5] Custom` | Select definitions, then choose individual / by namespace / combined packing |

When selecting definitions in modes [4] and [5], you can use `1,3,5` (comma-separated), `1-4` (range), `a` (select all). Enter `q` to confirm.

## Input Requirements

- **JSON**: Valid halo definition files, must contain a valid `id` field (e.g. `"halo:myhalo"`)
- **PNG**: Texture filenames must match those referenced by the `texture` fields in the JSONs
- Textures referenced in JSONs but missing from `input/` will trigger a warning

## Output Structure

Each generated `.zip` is a standard Minecraft resource pack:

```
<name>.zip
├── pack.mcmeta
└── assets/
    └── <namespace>/
        ├── halo_definitions/
        │   └── <name>.json
        └── textures/
            └── halo/
                └── <texture>.png
```

- `pack.mcmeta` is at the top level of the archive
- `pack_format` is fixed at 15 (Minecraft 1.20.x)
- On namespace collisions (two different namespaces using the same name), the filename is automatically prefixed with the namespace
