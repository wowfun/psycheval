# 输入与 Adapter

[English](../../../../user/peval/inputs-and-adapters.md)

## 文件与 ATIF

JSONL 每行包含一个 JSON 对象。每行可以是直接消息，也可以是带有
message、usage、metadata、accounting 和会话顺序的包装对象。CLI 还可读取
严格校验的 ATIF JSON、受支持的 Adapter JSON、Trial cell 及其中的轨迹工件。

## Harbor Trial 目录

传入 Harbor Trial 根目录，可在轨迹之外保留评测结果与 provenance：

```console
peval view tr -p <harbor-trial-dir>
```

该输入不需要 Adapter selector。MultiStepTrial 根目录会按 result 中的顺序，
为每个 Harbor step 生成一个 source。默认 inspect 可以表示尚无轨迹的失败或
运行中 step；完整报告要求选中的每个 source 都具有 ATIF 证据。直接传入
`agent/trajectory.json` 时只读取该 ATIF 文件，不推断其父 Trial。

```console
peval export tr -a opencode -p session.jsonl -o
peval view tr -m raw -p trajectory-opencode-session.json -o
```

内置 Adapter 的选择语义由 [CLI reference](../../../../reference/cli.md) 负责。
使用 `-d @adapter` 展开已配置的默认数据库，并通过 `--list`、
`--list-interactive` 和可重复的 `-s` 选择会话：

```console
peval view tr -d @opencode --list
peval view tr -m raw -d @hermes -s '#2' -o
```

多个数据库可使用从一开始计数的 DB 编号绑定 Adapter 和 session ID：

```console
peval view tr -m raw \
  -d ~/.hermes/state.db \
  -d ~/.local/share/opencode/opencode.db \
  -a d1=hermes -a d2=opencode \
  -s d1=<hermes-id> -s d2=<opencode-id> -o
```

## 自定义 Adapter

在提供 Adapter 的 distribution 的 `pyproject.toml` 中注册：

```toml
[project.entry-points."psycheval.adapters"]
custom = "custom_adapter:CustomAdapter"
```

Adapter 实现受支持的记录、路径或数据库转换方法；精确协议以源码和测试为准。
设置放在 `peval.toml` 的 `[adapters.<id>]` 下。
