import React, { useMemo, useState } from "react";
import { AuthPage } from "./pages/AuthPage.jsx";
import { Dashboard } from "./pages/Dashboard.jsx";
import { GoalsPage } from "./pages/GoalsPage.jsx";
import { TasksPage } from "./pages/CreateTaskPage.jsx";
import { RewardsPage } from "./pages/RewardsPage.jsx";
import { ScoringSchemesPage } from "./pages/ScoringSchemesPage.jsx";
import { ProfilePage } from "./pages/ProfilePage.jsx";
import { UpcomingPage } from "./pages/UpcomingPage.jsx";
import { mockLedgers, mockProfile, mockRewards, mockTasks } from "./data/mockData.js";

const tabs = [
  { id: "dashboard", label: "Dashboard" },
  { id: "upcoming", label: "Upcoming" },
  { id: "rewards", label: "Rewards" },
  { id: "profile", label: "Profile" }
];

export default function App() {
  const [isAuthed, setIsAuthed] = useState(false);
  const [activeTab, setActiveTab] = useState("dashboard");
  const [tasks, setTasks] = useState(mockTasks);

  const balance = useMemo(() => {
    return mockLedgers.reduce((total, item) => total + item.delta, 0);
  }, []);

  const completeTask = (taskId, level) => {
    setTasks((items) =>
      items.map((task) => {
        if (task.id !== taskId) return task;
        return {
          ...task,
          status: "done",
          completion_level: level,
          score_awarded: task.scoring_snapshot_json[level] ?? 0
        };
      })
    );
  };

  const currentPage = {
    dashboard: <Dashboard tasks={tasks} balance={balance} onComplete={completeTask} />,
    upcoming: <UpcomingPage tasks={tasks} />,
    goals: <GoalsPage />,
    tasks: <TasksPage tasks={tasks} setTasks={setTasks} />,
    rewards: <RewardsPage rewards={mockRewards} balance={balance} />,
    scoring: <ScoringSchemesPage />,
    profile: (
      <ProfilePage
        profile={mockProfile}
        ledgers={mockLedgers}
        balance={balance}
        onNavigate={setActiveTab}
      />
    )
  }[activeTab];

  if (!isAuthed) {
    return <AuthPage onEnter={() => setIsAuthed(true)} />;
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
      <main className="main-panel">{currentPage}</main>
    </div>
  );
}
