# 输入与 Adapter

## Path 与 ATIF

JSONL 每行接受一个对象，可以是直接 message，也可以是包含 `message`、
`usage`、`metadata`、`accounting` 和 `session_seq` 的 wrapper。

```bash
peval-py export tr -a opencode -p session.jsonl -o
peval-py view tr -m raw -p trajectory-opencode-session.json -o
```

导出的 ATIF JSON 不需要 adapter；在报告 metadata 中显示为 `atif`。

## 内置 Adapter

- `psychevo`：JSONL 和 Psychevo `state.db`，默认 DB 为
  `~/.psychevo/state.db`。
- `opencode`：JSONL 和 OpenCode SQLite，默认 DB 为
  `~/.local/share/opencode/opencode.db`。
- `hermes`：JSONL 和 Hermes SQLite，默认 DB 为 `~/.hermes/state.db`。
- `deepagents`：读取包含 `session_id`、`started_at`、`query`、`llm_steps`
  和 `tool_steps` 的单个顶层 JSON object；仅支持 path，没有默认 DB。

使用 `-d @adapter` 展开已配置的默认 DB。通过 `--list`、
`--list-interactive`、`-s ID` 或 `-s #N` 查看和选择 session：

```bash
peval-py view tr -d @opencode --list
peval-py view tr -m raw -d @hermes -s '#2' -o
```

多 DB 输入使用一基索引绑定 adapter 和 session：

```bash
peval-py view tr -m raw \
  -d ~/.hermes/state.db \
  -d ~/.local/share/opencode/opencode.db \
  -a d1=hermes -a d2=opencode \
  -s d1=<hermes-id> -s d2=<opencode-id> \
  -o
```

## 自动选择 Adapter

CLI path 会先按完整路径段或文件名 token 推断 adapter；多匹配直接失败，未匹配
则回退到配置或默认 adapter。工作台的 Path、DB 和 input-table 在 `auto` 下要求
唯一推断。JSONL upload 回退到当前配置；ATIF 和 report JSON upload 不需要 adapter。

## Input Table

CSV、JSON 和 XLSX 清单可以组合 path 与 DB。JSON 可以是顶层 array，也可以是带
`rows` 和 `report_notes` 的 object：

```json
{
  "report_notes": ["跨 Agent 对比。"],
  "rows": [
    {"path": "runs/hermes.jsonl", "adapter": "hermes", "alias": "Hermes"},
    {"db": "opencode.db", "session_id": "ses_123", "adapter": "opencode"}
  ]
}
```

`alias`、`label` 和 `source_alias` 等价。多行报告使用 `view tr -i`；
`export tr -i` 仍只接受一个 session。

## 自定义 Adapter

通过已安装包的 entry point 注册 adapter，entry point 名称就是 adapter id：

```toml
[project.entry-points."peval_py.adapters"]
custom = "custom_peval_adapter:CustomAdapter"
```

Adapter 至少实现 `convert(records, config)`、`convert_path(path, config)` 或
`convert_db(path, session_id, config)` 之一。专属配置位于 `[adapters.<id>]`。
保留键 `default_db_path` 会展开 `~`，相对路径基于定义它的配置文件解析，且不会
传给 adapter 实现。
