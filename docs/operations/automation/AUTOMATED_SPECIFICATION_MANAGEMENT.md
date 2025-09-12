# 📊 自動化規範管理標準 v0.2.0

## 📊 追蹤規範標準格式

### 追蹤規範模板結構

每個大型任務必須建立符合以下格式的追蹤規範：

```markdown
# 🎯 [任務名稱]大型任務追蹤清單 v0.2.0

## 📋 總覽
根據 CLAUDE.md 四大原則建立的系統性任務追蹤...

## 🗺️ 任務完整分析 (MECE 原則分解)
[按照 MECE 原則完全分解的任務清單]

## 🎯 詳細任務清單與執行狀態
[具體任務表格，包含狀態追蹤]

## 📊 進度統計
[量化進度指標]

## 🎯 階段化執行計劃 (82 法則優先級)
[按照 82 法則排序的執行階段]

## 🛠️ 實現標準 (SESE 原則)
[簡單、有效、系統、全面的實現標準]

## 🧪 驗收測試標準 (ICE 原則)
[直覺、精簡、覆蓋的測試標準]

## 🤖 自動化對話接軌指南
[一句話繼續執行指令與自動化協議]

## 🚀 當前執行狀態
[實時進度追蹤區塊]
```

### 必要引用規範

```markdown
## 📚 規範引用

本追蹤規範遵循以下核心規範：

- **[自動化開發規範](../../operations/automation/AUTOMATED_DEVELOPMENT_SPECIFICATION.md)** - 自動化迭代流程
- **[專案總規範](../../../CLAUDE.md)** - 四大原則與深度優化流程

### 自動化執行協議

本追蹤規範支持完全自動化執行，遵循自動化開發規範定義的迭代迴圈流程。
```

## 🔧 規範統一性檢查機制

### 自動統一性驗證

#### 版本號統一性檢查

```javascript
function check_version_consistency() {
  let all_specs = scan_all_specifications();
  
  // 檢查版本號是否統一為 v0.2.0
  for (let spec of all_specs) {
    if (spec.version !== "v0.2.0") {
      flag_version_inconsistency(spec);
    }
  }
}
```

#### 引用路徑統一性檢查

```javascript
function check_reference_consistency() {
  let all_references = scan_all_references();
  
  for (let ref of all_references) {
    if (!file_exists(ref.path)) {
      flag_broken_reference(ref);
    }
  }
}
```

### 自動化修復機制

- **版本號自動修正**: 自動更新為 v0.2.0 並 Git 提交
- **引用路徑自動修正**: 自動修正錯誤路徑並 Git 提交
- **格式標準自動調整**: 統一為模板格式

## 🔄 版本號管理規範

### 版本號標準格式

**統一版本號格式：`v0.2.0`**

- 所有追蹤規範：`v0.2.0`
- 所有技術規範：`v0.2.0`
- 所有實現標準：`v0.2.0`

**版本號升級條件**:
- `v0.2.x`: 小幅修正、優化
- `v0.x.0`: 功能新增、結構調整
- `vx.0.0`: 重大架構改變、里程碑達成

### 自動版本檢查腳本

```bash
#!/bin/bash
# 版本號統一檢查與修正腳本

check_and_fix_version_consistency() {
    local target_version="v0.2.0"
    local files_to_check=(
        "docs/operations/automation/AUTOMATED_DEVELOPMENT_SPECIFICATION*.md"
        "docs/**/*_MASTER_PLAN_v*.md"
    )

    for pattern in "${files_to_check[@]}"; do
        for file in $pattern; do
            if [[ -f "$file" ]]; then
                local current_version=$(grep -oP 'v\d+\.\d+\.\d+' "$file" | head -1)
                
                if [[ "$current_version" != "$target_version" ]]; then
                    echo "🔧 修正版本號: $file ($current_version → $target_version)"
                    sed -i "s/$current_version/$target_version/g" "$file"
                    
                    # 重新命名文件
                    local new_filename=$(echo "$file" | sed "s/$current_version/$target_version/g")
                    if [[ "$file" != "$new_filename" ]]; then
                        mv "$file" "$new_filename"
                        echo "📝 重新命名: $file → $new_filename"
                    fi
                fi
            fi
        done
    done
}
```

## 🚀 Git 提交規範

### 提交訊息格式標準

根據專案既有 commit 格式，採用以下標準格式：

```bash
# 功能新增
git commit -m "Establish automated development specification for meeting minutes

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 錯誤修復
git commit -m "fix: Unify version numbers across all tracking specifications

Update all tracking specifications to v0.2.0 for consistency

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 規範更新
git commit -m "Update automated development specification v0.2.0

Add meeting minutes processing workflow and optimization guidelines

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 提交格式模式

#### 1. 簡潔描述型（推薦，80% 使用）

```bash
# 格式: 動詞 + 簡潔描述
"Establish meeting minutes automation workflow"
"Optimize word template generation process"
"Refine PDF export functionality"
```

#### 2. 標準化前綴型（特定情況）

```bash
# 格式: type: 描述
"fix: Correct Ollama integration parameters"
```

#### 3. 複合描述型（複雜變更）

```bash
# 格式: 主要變更 | 次要變更
"Implement core meeting processing pipeline | Update documentation standards"
```

## 📚 相關規範

- **[自動化開發規範主檔案](./AUTOMATED_DEVELOPMENT_SPECIFICATION.md)**
- **[自動化工作流程](./AUTOMATED_DEVELOPMENT_WORKFLOW.md)**
- **[實施範例指南](./AUTOMATED_IMPLEMENTATION_EXAMPLES.md)**