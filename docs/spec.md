這是一份根據我們討論細節所彙整的資深工程級別 **PRD (產品需求文件)**。這份文件旨在指導開發團隊實作這套高度彈性的即時監控邏輯配置系統。

---

# 產品需求文件 (PRD): 即時監控物件邏輯配置系統

## 1. 專案概覽 (Project Overview)

本專案旨在建立一個可視化的流程配置平台，允許使用者透過 **React+Vite 前端畫布** 自由串接 Bounding Box 的處理邏輯（過濾、邏輯判斷、空間關係運算）。該流程最終導出為 JSON 描述檔，由 **Python 執行引擎** 在邊緣端或伺服器端進行即時（Single Frame）的推論與事件觸發。

---

## 2. 核心需求 (Core Requirements)

* **低延遲處理**：必須支援即時影像串流中的 Bounding Box 資料處理。
* **高度彈性**：支援自定義幾何偏移（Offset）與複雜的空間關係判定。
* **動態適配**：前端 UI 必須能根據不同的攝影機輸入（Class List）自動調整配置選項。
* **穩定性與效能**：具備 Top-K 篩選機制，防止物件過多時導致運算阻塞。預設K=1000
* **強型別校驗**：前端連線需具備型別檢查，確保 DAG 邏輯合法。

---

## 3. 核心功能 (Core Features)

### A. 三大核心區塊 (Nodes)

1. **過濾區塊 (Filter Block)**:
* 根據 `classname` 動態加載參數（如長、寬、信心度）。
* 支援大於、等於、小於的邏輯比較。
* 不符合條件者直接「丟棄 (Discard)」。


2. **邏輯運算區塊 (Logic Block)**:
* 接收匯集後的物件清單。
* 判斷特定類別的存在性（如：A 且 B 存在）。
* 輸出結果需包含「觸發標記 (Trigger Metadata)」。


3. **關係產生區塊 (Relation Block)**:
* 單一來源進行兩兩比對（Pairwise/Self-Join）。
* 支援 Overlap (IoU)、距離等空間關係判定。
* 產生新的 Bounding Box，並支援「自定義幾何偏移」。



### B. 資料流管理 (Data Flow)

* **DAG 架構**: 支援分支與匯集，非線性流水線。
* **保留副本**: 匯集節點不進行去重，保留各分支的處理譜系（Lineage）。
* **效能保護**: 支援設定處理上限，優先處理高信心度物件。

---

## 4. 核心組件 (Core Components)

### 前端組件 (Frontend)

* **Canvas Engine**: 基於 React-Flow 的畫布，負責節點渲染。
* **Schema Inferencer**: 遞迴搜尋上游節點，推導目前可用的 `class_list`。
* **Validation Layer**: 強型別插槽（Ports），區分 `BoxStream`, `LogicSignal`, `Collection`。

### 後端組件 (Backend/Python)

* **Interpreter**: 讀取 JSON 並實例化節點物件的執行器。
* **Spatial Engine**: 處理 IoU 計算與幾何變換的數學庫。
* **Dispatcher**: 負責將處理後的結果（含 Metadata）分發至報警系統或資料庫。

---

## 5. 應用/用戶流程 (App/User Flow)

1. **初始化**: 使用者選擇特定 CCTV 來源，前端加載該來源的物件類別。
2. **流程設計**:
* 從側邊欄拖入「過濾區塊」，系統自動感應類別並設定門檻。
* 將多個過濾結果連線至「匯集節點」。
* 串接「邏輯區塊」判定特定場景（如：禁止區域內人與車同時出現）。


3. **關係設定**: 串接「關係區塊」，定義若人車重疊，產生一個擴大 10% 的感興趣區域（RoI）。
4. **導出部署**: 導出 JSON 檔，Python 直譯器讀取後立即開始監控處理。

---

## 6. 技術棧 (Techstack)

* **Frontend**: React 18+, Vite, React-Flow (畫布核心), Zustand (狀態管理)。
* **Backend**: Python 3.9+, NumPy (矩陣運算), Pydantic (JSON Schema 校驗)。
* **Data Format**: JSON (基於 DAG 結構的描述檔)。
* **Communication**: 離線編輯模式（REST API 儲存/獲取配置）。

---

## 7. 實作計畫 (Implementation Plan)

| 階段 | 任務重點 | 關鍵產出 |
| --- | --- | --- |
| **Phase 1: 基礎架構** | 定義 JSON Schema 與 Python BaseNode 類別 | 數據協定規範 |
| **Phase 2: 前端畫布** | 整合 React-Flow，實作強型別連線與節點 UI | 可視化編輯器原型 |
| **Phase 3: 智慧推導** | 開發「上游推導」演算法，動態加載區塊參數 | 自動感應配置介面 |
| **Phase 4: 執行引擎** | 實作 Python Interpreter 與空間運算邏輯 | 可執行 Python Library |
| **Phase 5: 效能優化** | 加入 Top-K 篩選與幾何變換 Offset 功能 | 穩定版引擎 |

---
