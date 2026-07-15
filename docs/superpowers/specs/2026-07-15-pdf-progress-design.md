# PDF 处理进度条 设计文档

## 概述

为 PDF OCR 处理增加 tqdm 进度条显示，让用户在逐页识别 API 调用期间能看到实时进度。同时移除以命令行输出为目的的 `--stdout` 参数，统一为文件输出。

## 背景

当前 `ocr_file()` 对 PDF 逐页调用 OCR API 时没有任何进度提示。对于多页 PDF，用户只能等待，无法知道进度。同时 `--stdout` 参数的存在使得输出路径分裂为两条逻辑分支，增加复杂度。

## 改动范围

### 1. `ocr.py` — 核心改动

- 移除 `stdout` 参数，`ocr_file()` 签名简化为 `ocr_file(input_path, engine, pages=None) -> str`
- 始终将结果写入 `{input_path.stem}.txt`，移除 `print(merged)` 分支
- 在逐页 OCR 循环中引入 tqdm：

```python
from tqdm import tqdm

for i, img_path in enumerate(tqdm(images, file=sys.stderr, desc=f"识别 {input_path.name}")):
    text = engine.recognize(img_path)
    ...
```

进度条输出到 stderr，格式示例：`识别 input.pdf:  50%|█████     | 5/10 [00:25<00:25, 5.00s/it]`

### 2. `main.py` — 移除 --stdout

- 删除 `--stdout` argparse 参数定义
- 调用处移除 `stdout=args.stdout` 参数

### 3. `pyproject.toml` — 新增依赖

添加 `tqdm` 包。

### 4. `tests/test_ocr.py` — 测试更新

- 所有测试中 `ocr_file(..., stdout=True)` 改为 `ocr_file(...)` 
- `test_save_to_file` 移除 `unlink` 清理逻辑，因为默认行为就是保存文件

## 非改动范围

- `pdf_utils.py` 不增加进度条（PDF 渲染通常很快，不是瓶颈）
- `engines/` 目录不做任何改动
- 不引入回调/事件等解耦机制（YAGNI — 当前只有 CLI 一个调用方）

## 错误处理

进度条本身不引入新的错误场景。OCR 识别异常时，异常会中断 tqdm 迭代器但不影响异常传播。

## 依赖变更

| 操作 | 包 | 用途 |
|------|-----|------|
| 新增 | `tqdm` | 终端进度条显示 |
