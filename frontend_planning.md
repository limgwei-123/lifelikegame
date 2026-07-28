# Lifelikegame 前端重建規劃

> 本文件是 Lifelikegame 未來前端重建的主要討論與決策基準。Origtek 的架構另存於 `origtek_frontend_reference.md`，只作參考。

## 1. 評估基準

- Repository：`https://github.com/limgwei-123/lifelikegame`
- 評估分支：`main`
- 評估 Commit：`2fd8490c1a1ccca8c1e887539f8c11a9e2904ae6`

目前開發者正在持續優化後端。現有前端主要由 AI 生成，不要求保留既有前端架構或實作，因此可以在保留後端 API 與業務規則的前提下完整重建前端。

## 2. 專案規模與產品定位

評估時的約略規模：

- 前端約 35 個 JavaScript、JSX 和 CSS 檔案，約 3,700 行。
- 後端約 104 個 Python 檔案，約 2,900 行。
- 後端約 46 個 API Handler。
- 後端有 11 個 Pytest 測試檔案。
- `frontend/src/styles.css` 約 1,319 行。
- `frontend/src/App.jsx` 約 402 行。
- `frontend/src/pages/AiPlannerPage.jsx` 約 341 行。

Lifelikegame 不是普通 Todo App，而是遊戲化個人目標管理產品：

```text
Authentication
├── User Profile
├── Goals
├── Tasks
│   ├── Task Schedules
│   └── Daily Task Instances
├── Scoring Schemes
├── Point Ledgers
├── Rewards
├── Redemptions
├── Cross-module Workflows
└── AI Planner
```

核心流程：

```text
註冊或登入
    ↓
手動建立目標，或由 AI Planner 生成計畫
    ↓
在目標下建立 Tasks 和 Schedules
    ↓
後端產生每日 Task Instances
    ↓
使用者完成任務
    ↓
依 Scoring Scheme 寫入 Point Ledger
    ↓
使用積分兌換 Rewards
```

前端應以多個業務模組設計，而不是當成單一 Todo List。

## 3. 後端決策

後端保留並持續優化。

目前已按業務領域分模組：

```text
backend/app/
├── auth/
├── users/
├── goals/
├── tasks/
├── task_schedules/
├── task_instances/
├── scoring_schemes/
├── point_ledgers/
├── rewards/
├── redemptions/
├── workflows/
└── ai_planner/
```

多數模組包含：

```text
router
service
repository
schemas
models
interfaces
dependencies
```

後端已有 FastAPI、PostgreSQL、SQLAlchemy、Alembic、Pydantic、JWT、APScheduler、AI Planner 和 Pytest。這些業務邊界和測試具有保留價值。

前後端以 API Contract 獨立演進：

```text
React Frontend
    ↓ HTTP / JSON
FastAPI Backend
    ↓
Service / Repository / Workflow
    ↓
PostgreSQL
```

## 4. 現有前端問題

### `App.jsx` 責任過多

目前同時管理 Authentication、Token、Profile、Goals、Tasks、Schedules、Task Instances、Rewards、Points、Scoring Schemes、Loading、Error、CRUD、Sidebar 和頁面切換，已形成 God Component。

### 登入後一次載入所有資料

即使使用者沒有進入某個功能，也會載入 Profile、Goals、Tasks、Schedules、Rewards、Ledgers、Balance、Scoring Schemes 和 Task Instances。

未來應由每個 Route 或 Module 載入自己需要的資料。

### 沒有真正的 Router

目前以 `activeTab` 和 object map 決定頁面，造成：

- 沒有可分享 URL。
- 重新整理後無法保留頁面。
- 上一頁和下一頁不正常。
- Protected Route、詳細頁和 Lazy Loading 難以管理。

目標 URL：

```text
/dashboard
/upcoming
/goals
/tasks
/tasks/:taskId
/rewards
/scoring-schemes
/ai-planner
/profile
```

### Server State 全部使用 `useState`

後端資料需要手動載入、更新和刷新，容易產生重複請求、不同步、Loading 衝突和 Error handling 不一致。未來交由 TanStack Query 管理。

### 頁面元件過大

AI Planner Page 同時承擔 Chat、History、Prompt、Plan normalization、Plan editing、Task editing、Schedule editing、Validation、Confirmation 和 Saving。

目標拆分：

```text
AiPlannerPage
├── PlannerChat
├── PlannerMessageList
├── PlanReviewSheet
├── PlanTaskEditor
└── useAiPlanner
```

### 單一大型 CSS

目前樣式主要集中在約 1,319 行的 `styles.css`，容易發生命名衝突、無用樣式、跨頁影響及重複 CSS。

### 缺少 TypeScript

產品已有 Goal、Task、Schedule、TaskInstance、ScoringScheme、Reward、Ledger、Redemption 和 AiPlan 等多種關聯資料。純 JavaScript 難以可靠處理 Nullable、ID、API Payload、Response 和 Form Data。

### 缺少前端測試

後端已有測試，前端尚未建立正式測試基礎。

## 5. 最終重建決策

選擇：

> 保留並持續優化 FastAPI 後端，完整重建 TypeScript React 前端。

理由：

1. 現有前端由 AI 生成，不要求保留。
2. 前端約 3,700 行，仍在低成本重建範圍。
3. 後端業務複雜度已超過現有前端架構能舒服承載的程度。
4. 現在重建比未來增長至一兩萬行後再處理便宜。
5. 後端 API 和測試可作為新前端的穩定基礎。

不要先刪除舊前端。新前端應在新目錄或獨立分支完成，功能覆蓋並驗證後再替換。

## 6. 目標技術棧

```text
React
TypeScript
Vite 或 React Router Framework
React Router
TanStack Query
React Hook Form
Zod
shadcn/ui
```

| 工具 | 責任 |
|---|---|
| React | UI 與互動 |
| TypeScript | API、表單和業務資料型別 |
| React Router | URL、導航和 Protected Routes |
| TanStack Query | Server State、快取、Loading、Error 和刷新 |
| React Hook Form | 表單狀態 |
| Zod | 表單及資料邊界驗證 |
| shadcn/ui | Button、Input、Dialog、Sheet、Card 等基礎 UI |

第一階段不需要 Redux、大型全域 Store、自製完整 Design System、Micro Frontend 或 Origtek 式大型 Toolbar 和 Grid 包裝。

## 7. 目標目錄結構

```text
frontend/
└── src/
    ├── app/
    │   ├── App.tsx
    │   ├── router.tsx
    │   ├── providers.tsx
    │   └── queryClient.ts
    │
    ├── components/
    │   ├── ui/
    │   │   ├── button.tsx
    │   │   ├── input.tsx
    │   │   ├── dialog.tsx
    │   │   ├── sheet.tsx
    │   │   └── card.tsx
    │   │
    │   └── layout/
    │       ├── AppShell.tsx
    │       ├── Sidebar.tsx
    │       └── PageHeader.tsx
    │
    ├── modules/
    │   ├── auth/
    │   ├── dashboard/
    │   ├── goals/
    │   ├── tasks/
    │   ├── schedules/
    │   ├── scoring/
    │   ├── points/
    │   ├── rewards/
    │   ├── profile/
    │   └── ai-planner/
    │
    ├── lib/
    │   ├── apiClient.ts
    │   ├── authToken.ts
    │   └── date.ts
    │
    ├── types/
    │   └── api.ts
    │
    └── main.tsx
```

模組依賴方向：

```text
modules/*
    ↓
components/ui + components/layout + lib
    ↓
React + shadcn/ui + Backend API
```

規則：

1. `components/ui` 不包含 Goal、Task 或 Reward 等業務語意。
2. 業務元件留在所屬 Module。
3. Module 不直接讀取其他 Module 的內部檔案。
4. 跨模組流程使用公開入口或 Workflow API。
5. 真正重複兩至三次後才抽取更高層共用元件。

## 8. 業務模組結構

例如 Goals：

```text
modules/goals/
├── api/
│   └── goalsApi.ts
├── components/
│   ├── GoalCard.tsx
│   ├── GoalForm.tsx
│   └── GoalList.tsx
├── hooks/
│   ├── useGoals.ts
│   ├── useCreateGoal.ts
│   └── useUpdateGoal.ts
├── pages/
│   └── GoalsPage.tsx
├── schemas/
│   └── goalSchema.ts
├── types/
│   └── goal.ts
└── index.ts
```

AI Planner：

```text
modules/ai-planner/
├── api/
├── components/
│   ├── PlannerChat.tsx
│   ├── PlannerMessageList.tsx
│   ├── PlanReviewSheet.tsx
│   └── PlanTaskEditor.tsx
├── hooks/
│   └── useAiPlanner.ts
├── pages/
│   └── AiPlannerPage.tsx
└── schemas/
```

AI Planner 依賴 Goals、Tasks、Schedules、Scoring Schemes 和 Workflow API，因此最後重建。

## 9. API 與型別策略

保留現有 API Client 的概念：

- API Base URL
- Token
- Authorization Header
- Response Parsing
- 統一 Error
- 401 清除 Token

改寫成 TypeScript：

```typescript
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  // 加入 Token、解析 Response、處理錯誤
}
```

FastAPI 已提供 OpenAPI Schema。未來應考慮：

- 從 OpenAPI 產生 TypeScript Types。
- 從 OpenAPI 產生 API Client。
- 在 CI 檢查 API Contract 變更。
- 減少後端優化期間的前後端欄位不一致。

如果後端 DTO 與畫面需求不同，使用 Mapper：

```text
Backend DTO
    ↓ mapper
Frontend Model
    ↓
UI Component
```

不要在 `App.tsx` 或 Page 中臨時拼接大量關聯資料。

## 10. 狀態管理策略

### Server State

交給 TanStack Query：

```text
Profile
Goals
Tasks
Task Schedules
Task Instances
Scoring Schemes
Point Ledgers
Balance
Rewards
Redemptions
```

Mutation 成功後使用 Query Invalidation，而不是在 `App.tsx` 手動維護所有陣列。

### 全域 Client State

只保存真正全域的狀態：

```text
目前使用者
登入狀態
Theme
Sidebar 是否展開
```

### 頁面本地狀態

留在 Page、Component 或 Custom Hook：

```text
Dialog 是否開啟
目前編輯哪一筆
頁面 Tab
表單輸入
AI Planner 草稿
Plan Review 狀態
```

## 11. UI 元件策略

### 基礎 UI

放在 `components/ui`：

- Button
- Input
- Textarea
- Checkbox
- Select
- Dialog
- Sheet
- Card
- Badge
- Tabs

這一層使用或小幅調整 shadcn/ui，不包含業務規則。

### Layout

放在 `components/layout`：

- AppShell
- Sidebar
- TopBar
- PageHeader
- MobileNavigation

### 業務元件

放在所屬 Module：

```text
modules/tasks/components/TaskCard.tsx
modules/goals/components/GoalForm.tsx
modules/rewards/components/RewardDialog.tsx
```

Lifelikegame 不需要一開始建立 Origtek 式 `shared-button`、`shared-toolbar`、`shared-grid` 和 SQL Filter 包裝。消費者產品應保持更直接的元件組合。

## 12. 重建順序

建立 `frontend-next/` 或獨立分支，依序完成：

1. TypeScript React 專案。
2. App Providers、Router 和 Query Client。
3. `components/ui` 和基本 Theme。
4. App Shell、Sidebar 和 Responsive Navigation。
5. API Client。
6. Authentication 和 Protected Routes。
7. Goals。
8. Tasks 和 Schedules。
9. Dashboard 和 Task Completion。
10. Scoring Schemes。
11. Points、Rewards 和 Redemptions。
12. Profile。
13. AI Planner。
14. 前端測試。
15. 所有後端流程整合驗證。
16. 功能覆蓋完成後替換舊 `frontend/`。

## 13. 測試策略

### 單元測試

- Mapper
- Zod Schema
- Schedule formatter
- Query helpers
- Route 和權限判斷

### Component 測試

- Login Form
- Goal Form
- Task Form
- Schedule Fields
- Task Completion Dialog
- Reward Redemption Dialog
- AI Plan Review

### 整合流程

```text
註冊 → 登入
建立 Goal
建立 Task 和 Schedule
取得 Task Instance
完成 Task
獲得 Points
建立 Reward
兌換 Reward
AI 生成 Plan
確認並建立 Goal、Tasks、Schedules
```

後端持續優化時，特別驗證 Request、Response、Error、Authentication Header、ID、Nullable、日期和時區格式。

## 14. 前後端協作原則

1. 後端更改 Schema 時同步更新 OpenAPI。
2. 前端以 API Contract 為邊界，不依賴後端內部 Model。
3. 每完成一個前端 Module，就與真實後端整合。
4. 不必等待所有後端功能完全完成才開始前端。
5. 尚未穩定的 API 先建立明確 Adapter。
6. AI 產生的 Component 必須符合既定目錄、型別和依賴規則。
7. 不因 AI 能快速產生程式碼而省略測試和模組邊界。
8. 舊前端只作為功能和視覺參考，不作為新架構模板。

## 15. 最終方向

```text
保留並持續優化 FastAPI Backend
                ↓
以 OpenAPI / HTTP Contract 作為邊界
                ↓
完整重建 TypeScript React Frontend
                ↓
使用 Modules 組織業務功能
                ↓
使用 TanStack Query 管理 Server State
                ↓
使用 shadcn/ui 建立一致的消費者產品 UI
```

新前端的目標是：

- 模組化
- 型別安全
- API 驅動
- 路由清楚
- 狀態責任明確
- 易於測試
- 適合消費者產品
- 對初學者和 AI 都容易理解及維護
