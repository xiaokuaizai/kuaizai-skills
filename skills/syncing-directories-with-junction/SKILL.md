---
name: syncing-directories-with-junction
description: Use when user wants two local Windows directory paths to always stay in sync in real time - e.g. one path is auto-synced to git/cloud (Obsidian vault, xkz_note, etc.) and the other is a working location that should mirror it. Covers pre-merge checks, Junction creation, and safe-removal rules.
---

# Syncing Directories with Junction

## Overview

用 Windows 目录联接（Junction）让两个本地路径指向**同一份物理数据**，实现零延迟、零冲突的"同步"。

**核心原理：** Junction 不是真的复制两份数据来回同步，而是给一份数据开两个访问路径。在任一路径的读写删操作 = 操作同一份数据。

**适用场景：** 路径 A 已有自动同步机制（Obsidian git 插件、xkz_note 程序等），路径 B 是日常工作入口，希望 B 改了 A 也"自动同步"。

**强交互原则：** 每一步执行前明确告知用户"我将做什么"，执行后报告结果，等用户确认再进入下一步。遇到 Red Flags 必须停下询问。

## When to Use

**适合用 Junction：**
- 两个路径在同一台 Windows 机器上（NTFS 本地盘）
- 一个路径已有 git/云同步（A），另一个是工作入口（B）
- 用户希望"零延迟、零冲突、无后台进程"
- A 的同步配置不能改动

**不适合用 Junction：**
- 两台不同设备（用 Syncthing / 云盘）
- 需要两份独立物理副本（用 robocopy 定时双向）
- 跨文件系统或网络路径（Junction 只支持本地 NTFS）
- 用户可能频繁误删 B 内文件（Junction 删 B 内容 = 删 A 真实数据）

## 三种方案对比

| 维度 | Junction | robocopy 定时 | Syncthing |
|------|----------|---------------|-----------|
| 实时性 | ✅ 零延迟 | ❌ 几分钟延迟 | ✅ 近实时 |
| 冲突可能 | ✅ 无 | ⚠️ 同时改会冲突 | ⚠️ 有冲突文件 |
| 后台进程 | ❌ 无 | ✅ 计划任务 | ✅ 常驻 |
| 两份副本 | ❌ 一份 | ✅ 两份 | ✅ 两份 |
| 误删影响 | ⚠️ 删B=删A | ✅ 互不影响 | ✅ 互不影响 |
| 配置复杂度 | 低 | 中 | 高 |

## 关键决策：哪个路径作为 A（真实数据源）？

- **A = 已有 git/云同步配置的那个路径**（被指向、保留实体）
- **B = 工作入口、无同步配置的那个路径**（删除后建 Junction 指向 A）

**为什么不能反过来？** 如果删 A 建 Junction 指向 B，A 上原有的 git 同步配置会失效（Junction 路径下的 .git 不再是真实 .git）。

## 执行前的关键检查（4 项，踩坑预警）

### 检查 1：B 路径是否被其他程序占用

```powershell
# 检查 Obsidian / IDE / 编辑器是否打开了 B 内文件
Get-Process | Where-Object { $_.ProcessName -match "obsidian|code|cursor|typora" -or $_.MainWindowTitle -match "wiki|note" } | Select-Object Id, ProcessName, MainWindowTitle
```

**若有程序占用：必须停下，让用户关闭相关标签页或退出程序。** 否则：
- 删除 B 时可能被拒绝（文件句柄占用）
- 已打开的 B 文件在 Junction 后会失效（路径关系变化）
- Obsidian 的 vault 自动备份可能误判变化

### 检查 2：B 路径的 git 跟踪状态

```powershell
# B 是否在某个父 git 仓库内
Set-Location "B路径"
git rev-parse --show-toplevel 2>&1

# B 自身是否有 .git（是否是独立仓库）
Test-Path "B路径\.git"

# B 内文件是否被父仓库跟踪
git ls-files "B相对路径" 2>&1 | Select-Object -First 5
```

**若 B 被 git 跟踪：必须告知用户**，让用户决定是否将 B 加入父仓库的 .gitignore。否则 Junction 后父仓库会持续看到 A 的变化，造成 git status 噪音甚至误提交。

### 检查 3：A 路径的同步机制

```powershell
# A 的上级目录是否有 .git（判断 A 是否在 git 同步范围内）
Test-Path "A父路径\.git"

# 查看最近的 commit（判断同步机制是定时还是手动）
Set-Location "A父路径"
git log --oneline -5
```

**判断同步机制：**
- commit message 是 `vault backup: 时间戳` -> Obsidian git 插件自动备份（合并后会自动 commit + push）
- commit message 是手写的 -> 手动提交（合并后需提醒用户手动 commit）

### 检查 4：双向文件差异对比（不能只看目录时间戳）

**目录时间戳会被 git checkout 等操作刷新，不能反映文件真实新旧。必须做完整文件级对比。**

```powershell
$a = "A路径"; $b = "B路径"
# 列出 A 所有文件的时间戳和大小
Get-ChildItem $a -Recurse -Force -File | ForEach-Object { "{0}  {1}  {2} bytes" -f $_.LastWriteTime.ToString("MM-dd HH:mm:ss"), $_.FullName.Substring($a.Length+1), $_.Length } | Sort-Object
# 列出 B 所有文件的时间戳和大小
Get-ChildItem $b -Recurse -Force -File | ForEach-Object { "{0}  {1}  {2} bytes" -f $_.LastWriteTime.ToString("MM-dd HH:mm:ss"), $_.FullName.Substring($b.Length+1), $_.Length } | Sort-Object
```

**若有差异：必须先双向合并（见 Step 1），不能直接覆盖任一方。**

## 执行流程（5 步）

每步执行后必须报告结果，等用户确认再继续下一步。

### Step 1: 双向 robocopy 合并

```powershell
$a = "A路径"; $b = "B路径"
# A -> B：A独有的复制到B，A较新的覆盖B
robocopy $a $b /E /XO /R:1 /W:1 /NP /NDL
# B -> A：B独有的复制到A，B较新的覆盖A
robocopy $b $a /E /XO /R:1 /W:1 /NP /NDL
```

**参数说明：**
- `/E` 包含所有子目录（含空目录）
- `/XO` eXclude Older - 不用旧文件覆盖新文件
- `/R:1 /W:1` 失败重试1次，间隔1秒（避免卡住）
- `/NP /NDL` 不显示进度百分比和目录列表（减少输出噪音）

**踩坑预警：** `/XO` 对"目标不存在"的文件会跳过（没有比较基准）。所以**必须双向各跑一次**，才能让两边的并集都进入对方。只跑单向会导致一边缺文件。

### Step 2: 验证一致性

```powershell
$a = "A路径"; $b = "B路径"
# 双向 /L /MIR 只列出不执行
robocopy $a $b /L /MIR /NP /NDL /NS /NC /NJH
robocopy $b $a /L /MIR /NP /NDL /NS /NC /NJH
# 退出码 0 = 完全一致
```

**若任一方向退出码非 0：必须查清差异原因，不能进入 Step 3。**

### Step 3: 删除 B 目录

```powershell
Remove-Item "B路径" -Recurse -Force
# 确认已删除
Test-Path "B路径"  # 应返回 False
```

**仅在 Step 2 双向验证都通过后执行。** 此时 B 内容已和 A 一致，删除安全。

### Step 4: 创建 Junction

```powershell
cmd /c mklink /J "B路径" "A路径"
```

**参数说明：**
- `/J` 创建 Junction（目录联接），**不需要管理员权限**
- 参数顺序：先 B（联接名），后 A（目标）

**验证 Junction 已创建：**
```powershell
Get-Item "B路径" -Force | Select-Object Name, Mode, LinkType, Target
# LinkType 应为 Junction，Target 应指向 A
```

### Step 5: 验证 Junction 双向通透

```powershell
$a = "A路径"; $b = "B路径"
# 1. 文件数对比（应相等）
(Get-ChildItem $a -Recurse -Force -File).Count
(Get-ChildItem $b -Recurse -Force -File).Count

# 2. 在 B 建测试文件，去 A 确认
$test = "_junction_test.txt"
Set-Content -Path "$b\$test" -Value "test from B"
Test-Path "$a\$test"  # 应返回 True

# 3. 在 A 删测试文件，去 B 确认
Remove-Item "$a\$test" -Force
Test-Path "$b\$test"  # 应返回 False
```

## Quick Reference

| 步骤 | 命令 | 验证 |
|------|------|------|
| 合并 | `robocopy $a $b /E /XO; robocopy $b $a /E /XO` | 双向都执行 |
| 一致性 | `robocopy $a $b /L /MIR; robocopy $b $a /L /MIR` | 退出码 0 |
| 删 B | `Remove-Item $b -Recurse -Force` | `Test-Path $b` = False |
| 建 Junction | `cmd /c mklink /J "$b" "$a"` | LinkType = Junction |
| 验证 | 建测试文件双向确认 | A、B 文件数相等 |

## Common Mistakes

### 只跑单向 robocopy
- **问题：** `/XO` 不会把目标不存在的文件复制过去，导致一边缺文件
- **修复：** 必须双向各跑一次（A->B 和 B->A）

### 跳过一致性验证直接删 B
- **问题：** 合并可能不完整（权限、占用、隐藏文件），删了就丢数据
- **修复：** Step 2 双向 `/L /MIR` 退出码必须都是 0

### 只看目录时间戳判断差异
- **问题：** git checkout 等操作会刷新目录时间戳，文件时间戳可能未变；反之亦然
- **修复：** 必须用 `Get-ChildItem -Recurse -File` 列出每个文件的 LastWriteTime + Length 对比

### 忽略程序占用就直接删 B
- **问题：** Obsidian / IDE 持有文件句柄，删除可能失败或导致程序状态异常
- **修复：** 检查 1 必须先做，让用户关闭相关标签页

### 用 Symbolic Link 代替 Junction
- **问题：** Symbolic Link 需要管理员权限，且部分工具兼容性差
- **修复：** 本地目录联接一律用 `/J`（Junction）

## Red Flags - STOP

遇到以下情况必须停下，告知用户，等确认后再继续：

- B 内有程序正在打开文件（Obsidian 标签页、IDE 编辑器、终端 cd 进去）
- B 被 git 跟踪且未加入 .gitignore
- A 的同步机制未明（不知道是定时还是手动）
- 双向 robocopy 后仍有差异
- 用户希望两份独立物理副本（应改用 robocopy 定时方案）
- 路径在网络盘或非 NTFS 文件系统（Junction 不支持）

## Safe Removal（如何安全移除 Junction）

将来不想要 Junction 时，**必须区分"删联接"和"删内容"**：

```powershell
# ✅ 正确：只删联接本身，A 数据安全
rmdir "B路径"
# 或
Remove-Item "B路径"  # 注意：不要加 -Recurse -Force
```

```powershell
# ❌ 危险：会真实删除 A 的文件！
Remove-Item "B路径" -Recurse -Force
del /s /q "B路径"
# 资源管理器进 B 后 Shift+Delete 文件
```

**核心区别：**
- `rmdir` / 不带 `-Recurse` 的 `Remove-Item` -> 只删联接本身（A 数据完好）
- `-Recurse -Force` / `del /s` -> 先递归删内容（即 A 的真实文件）再删联接（数据丢失！）

**记忆口诀：删 Junction 用 rmdir，永远不要 -Recurse。**

## 术语辨析

| 类型 | 命令 | 权限 | 跨网络 | 用途 |
|------|------|------|--------|------|
| Junction | `mklink /J` | 普通 | ❌ | 本地目录联接（推荐） |
| Symbolic Link | `mklink /D` | 管理员 | ✅ | 目录符号链接 |
| Hard Link | `mklink /H` | 普通 | ❌ | 文件硬链接（非目录） |

本 skill 一律用 Junction（`/J`），因为：
1. 不需要管理员权限
2. 本地目录联接场景下行为最稳定
3. Obsidian、IDE、git 等工具对 Junction 兼容性最好

## Integration

**前置依赖：** 无

**完成后建议：**
- 把 Junction 配置（A 路径、B 路径、创建时间）写入项目记忆系统（memory）
- 在项目 CLAUDE.md 中提示此 Junction 的存在和移除规则
- 将来用户问"如何删除某目录"前，先检查该路径是否为 Junction（`Get-Item $path -Force | Select-Object LinkType`）

**相关 skill：** 无
