# 光环资源包打包工具

将裸的 JSON 定义文件和 PNG 贴图一键打包为可直接使用的 Minecraft 资源包（`.zip`）。

## 使用方法

1. 将你的光环定义文件（`.json`）和贴图文件（`.png`）放入 `input/` 文件夹
2. 运行脚本：

```bash
python3 packer.py
```

3. 脚本会扫描 `input/` 中的所有文件，展示发现的定义及其引用的贴图
4. 从交互菜单中选择打包方式，打包结果输出到 `output/`

## 打包模式

| 选项 | 说明 |
|------|------|
| `[1] Individual` | 每个光环定义单独打包为一个资源包 |
| `[2] By namespace` | 按命名空间分组，每个命名空间下的光环合并为一个资源包 |
| `[3] Combined` | 所有光环定义合并为一个资源包 |
| `[4] Pick` | 手动选择若干个定义，各自单独打包 |
| `[5] Custom` | 手动选择定义后，再选择按 individual / namespace / combined 方式打包 |

模式 [4] 和 [5] 中选择定义时，支持 `1,3,5`（逗号分隔）、`1-4`（范围）、`a`（全选），输入 `q` 确认完成。

## 输入文件要求

- **JSON**：合法的光环定义文件，必须包含有效的 `id` 字段（如 `"halo:myhalo"`）
- **PNG**：贴图文件名需与 JSON 中 `texture` 字段引用的文件名一致
- JSON 中引用但 `input/` 中不存在的贴图会有警告提示

## 输出结构

每个生成的 `.zip` 文件内部结构为标准的 Minecraft 资源包：

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

- `pack.mcmeta` 在压缩包最上层
- `pack_format` 固定为 15（Minecraft 1.20.x）
- 命名空间冲突时（两个不同命名空间使用了相同名称），文件名会自动加上命名空间前缀
