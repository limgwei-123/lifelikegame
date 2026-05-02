import React, { useCallback, useEffect, useMemo, useState } from "react";
import { login as loginRequest, signup as signupRequest } from "./api/authApi.js";
import { clearToken, getToken, setToken } from "./api/client.js";
import {
  createGoal,
  deleteGoal as deleteGoalRequest,
  listGoals,
  updateGoal
} from "./api/goalsApi.js";
import { getPointsBalance, listPointLedgers } from "./api/pointsApi.js";
import {
  createReward,
  deleteReward as deleteRewardRequest,
  listRewards,
  updateReward
} from "./api/rewardsApi.js";
import { listScoringSchemes } from "./api/scoringSchemesApi.js";
import {
  createTaskSchedule,
  listTaskSchedules,
  updateTaskSchedule
} from "./api/taskSchedulesApi.js";
import { completeTaskInstance, listTaskInstancesByDate } from "./api/taskInstancesApi.js";
import {
  deleteTask as deleteTaskRequest,
  listTasks,
  updateTask
} from "./api/tasksApi.js";
import { getMe } from "./api/usersApi.js";
import { confirmAiPlan, createTaskWithSchedule, redeemReward } from "./api/workflowsApi.js";
import { AiPlannerPage } from "./pages/AiPlannerPage.jsx";
import { AuthPage } from "./pages/AuthPage.jsx";
import { Dashboard } from "./pages/Dashboard.jsx";
import { GoalsPage } from "./pages/GoalsPage.jsx";
import { TasksPage } from "./pages/CreateTaskPage.jsx";
import { RewardsPage } from "./pages/RewardsPage.jsx";
import { ScoringSchemesPage } from "./pages/ScoringSchemesPage.jsx";
import { ProfilePage } from "./pages/ProfilePage.jsx";
import { UpcomingPage } from "./pages/UpcomingPage.jsx";
import { formatScheduleLabel, formatSimpleScheduleLabel } from "./utils/scheduleLabels.js";

const tabs = [
  { id: "dashboard", label: "Dashboard" },
  { id: "upcoming", label: "Upcoming" },
  { id: "ai", label: "AI" },
  { id: "rewards", label: "Rewards" },
  { id: "profile", label: "Profile" }
];

const todayIso = () => new Date().toISOString().slice(0, 10);

function mapInstance(instance, task, goal, schedule) {
  const scoring = instance.scoring_snapshot_json || task?.scoring_scheme_json || { done: 1 };

  return {
    ...instance,
    title: task?.title ?? `Task #${instance.task_id}`,
    description: task?.description ?? "",
    goal: goal?.title ?? "Goal",
    generated_reason: instance.generated_reason || schedule?.schedule_type || "scheduled",
    schedule_label: formatSimpleScheduleLabel(
      schedule?.schedule_type ?? instance.generated_reason,
    ),
    scoring_snapshot_json: scoring
  };
}

function mapTask(task, goals, schedules) {
  const goal = goals.find((item) => item.id === task.goal_id);
  const schedule = schedules.find((item) => item.task_id === task.id);

  return {
    ...task,
    goal: goal?.title ?? "Goal",
    goal_title: goal?.title ?? "Goal",
    generated_reason: schedule?.schedule_type ?? "daily",
    schedule_label: formatScheduleLabel(schedule?.schedule_type ?? "daily", schedule?.schedule_value_json),
    schedule_id: schedule?.id ?? null,
    schedule_value_json: schedule?.schedule_value_json ?? {},
    schedule_start_date: schedule?.start_date ?? "",
    schedule_end_date: schedule?.end_date ?? "",
    schedule_date: schedule?.schedule_type === "once" ? schedule?.start_date ?? "" : ""
  };
}

function buildSchedulePayload(data, scheduleType) {
  const startDate = data.schedule_date || data.start_date || null;

  if (!scheduleType) return null;

  return {
    schedule_type: scheduleType,
    schedule_value_json:
      scheduleType === "weekly"
        ? { days: data.weekly_days?.map(Number) ?? [] }
        : scheduleType === "monthly"
          ? { day: Number(data.monthly_day) || 1 }
          : scheduleType === "once"
            ? { date: startDate }
            : {},
    start_date: startDate,
    end_date: scheduleType === "once" ? startDate : data.end_date || null
  };
}

export default function App() {
  const [isAuthed, setIsAuthed] = useState(Boolean(getToken()));
  const [activeTab, setActiveTab] = useState("dashboard");
  const [profile, setProfile] = useState(null);
  const [goals, setGoals] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [taskInstances, setTaskInstances] = useState([]);
  const [taskSchedules, setTaskSchedules] = useState([]);
  const [rewards, setRewards] = useState([]);
  const [ledgers, setLedgers] = useState([]);
  const [balance, setBalance] = useState(0);
  const [scoringSchemes, setScoringSchemes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const dashboardTasks = useMemo(() => {
    return taskInstances.map((instance) => {
      const task = tasks.find((item) => item.id === instance.task_id);
      const goal = goals.find((item) => item.id === task?.goal_id);
      const schedule = taskSchedules.find((item) => item.id === instance.task_schedule_id);
      return mapInstance(instance, task, goal, schedule);
    });
  }, [goals, taskInstances, taskSchedules, tasks]);

  const taskTemplates = useMemo(() => {
    return tasks.map((task) => mapTask(task, goals, taskSchedules));
  }, [goals, taskSchedules, tasks]);

  const loadProtectedData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [
        me,
        goalList,
        taskList,
        scheduleList,
        rewardList,
        ledgerList,
        balanceData,
        scoringList,
        instanceList
      ] = await Promise.all([
        getMe(),
        listGoals(),
        listTasks(),
        listTaskSchedules(),
        listRewards(),
        listPointLedgers(),
        getPointsBalance(),
        listScoringSchemes(),
        listTaskInstancesByDate(todayIso())
      ]);

      setProfile(me);
      setGoals(goalList);
      setTasks(taskList);
      setTaskSchedules(scheduleList);
      setRewards(rewardList);
      setLedgers(ledgerList);
      setBalance(balanceData.balance ?? 0);
      setScoringSchemes(scoringList);
      setTaskInstances(instanceList);
    } catch (err) {
      setError(err.message);
      if (err.message.toLowerCase().includes("not authenticated")) {
        clearToken();
        setIsAuthed(false);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthed) {
      loadProtectedData();
    }
  }, [isAuthed, loadProtectedData]);

  const handleAuth = async ({ mode, email, password }) => {
    if (mode === "signup") {
      await signupRequest({ email, password });
    }
    const token = await loginRequest({ email, password });
    setToken(token.access_token);
    setIsAuthed(true);
  };

  const refreshPoints = async () => {
    const [ledgerList, balanceData] = await Promise.all([listPointLedgers(), getPointsBalance()]);
    setLedgers(ledgerList);
    setBalance(balanceData.balance ?? 0);
  };

  const refreshTasks = async () => {
    const [taskList, scheduleList, instanceList] = await Promise.all([
      listTasks(),
      listTaskSchedules(),
      listTaskInstancesByDate(todayIso())
    ]);
    setTasks(taskList);
    setTaskSchedules(scheduleList);
    setTaskInstances(instanceList);
  };

  const completeTask = async (taskInstanceId, level) => {
    await completeTaskInstance(taskInstanceId, { completion_level: level });
    await Promise.all([refreshTasks(), refreshPoints()]);
  };

  const saveGoal = async (goal, payload) => {
    const nextGoal = {
      ...payload,
      start_date: payload.start_date || null,
      target_date: payload.target_date || null,
      current_value: payload.current_value || null,
      target_value: payload.target_value || null
    };

    if (goal) {
      await updateGoal(goal.id, nextGoal);
    } else {
      await createGoal(nextGoal);
    }
    setGoals(await listGoals());
  };

  const removeGoal = async (goalId) => {
    await deleteGoalRequest(goalId);
    setGoals(await listGoals());
  };

  const saveTask = async (task, data) => {
    const taskPayload = {
      title: data.title,
      description: data.description || null,
      is_active: true,
      scoring_scheme_id: data.scoring_scheme_id ? Number(data.scoring_scheme_id) : null,
      is_scoring_scheme_locked: false
    };
    const schedulePayload = buildSchedulePayload(data, data.schedule_type);

    if (task) {
      await updateTask(task.id, taskPayload);
      if (schedulePayload) {
        if (task.schedule_id) {
          await updateTaskSchedule(task.schedule_id, schedulePayload);
        } else {
          await createTaskSchedule(task.id, schedulePayload);
        }
      }
    } else {
      await createTaskWithSchedule(Number(data.goal_id), {
        task: taskPayload,
        schedule: schedulePayload
      });
    }
    await refreshTasks();
  };

  const removeTask = async (taskId) => {
    await deleteTaskRequest(taskId);
    await refreshTasks();
  };

  const saveReward = async (reward, payload) => {
    if (reward) {
      await updateReward(reward.id, payload);
    } else {
      await createReward(payload);
    }
    setRewards(await listRewards());
  };

  const removeReward = async (rewardId) => {
    await deleteRewardRequest(rewardId);
    setRewards(await listRewards());
  };

  const handleRedeemReward = async (rewardId) => {
    await redeemReward(rewardId);
    const [rewardList] = await Promise.all([listRewards(), refreshPoints()]);
    setRewards(rewardList);
  };

  const handleConfirmAiPlan = async (plan) => {
    await confirmAiPlan(plan);
    await loadProtectedData();
    setActiveTab("dashboard");
  };

  const logout = () => {
    clearToken();
    setIsAuthed(false);
    setProfile(null);
    setActiveTab("dashboard");
  };

  const currentPage = {
    dashboard: <Dashboard tasks={dashboardTasks} balance={balance} onComplete={completeTask} />,
    upcoming: <UpcomingPage goals={goals} taskSchedules={taskSchedules} tasks={tasks} />,
    ai: <AiPlannerPage onConfirmPlan={handleConfirmAiPlan} />,
    goals: <GoalsPage goals={goals} onDelete={removeGoal} onSave={saveGoal} />,
    tasks: (
      <TasksPage
        goals={goals}
        scoringSchemes={scoringSchemes}
        tasks={taskTemplates}
        onDelete={removeTask}
        onSave={saveTask}
      />
    ),
    rewards: (
      <RewardsPage
        rewards={rewards}
        balance={balance}
        onDelete={removeReward}
        onRedeem={handleRedeemReward}
        onSave={saveReward}
      />
    ),
    scoring: <ScoringSchemesPage schemes={scoringSchemes} onReload={loadProtectedData} />,
    profile: (
      <ProfilePage
        profile={profile}
        ledgers={ledgers}
        balance={balance}
        onLogout={logout}
        onNavigate={setActiveTab}
      />
    )
  }[activeTab];

  if (!isAuthed) {
    return <AuthPage onSubmit={handleAuth} />;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">LG</div>
          <div>
            <p className="eyebrow">Life OS</p>
            <h1>lifelikegame</h1>
          </div>
        </div>
        <nav className="nav-list" aria-label="Main sections">
          {tabs.map((tab) => (
            <button
              className={activeTab === tab.id ? "nav-item active" : "nav-item"}
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="main-panel">
        {error ? <p className="empty-text">{error}</p> : null}
        {loading ? <p className="empty-text">Loading...</p> : currentPage}
      </main>
    </div>
  );
}
