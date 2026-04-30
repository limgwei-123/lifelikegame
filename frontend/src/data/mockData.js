export const mockTasks = [
  {
    id: 1,
    title: "Morning workout",
    goal: "Build consistent fitness",
    description: "Strength training before work.",
    status: "todo",
    completion_level: null,
    score_awarded: 0,
    generated_reason: "daily",
    scoring_snapshot_json: { perfect: 3, normal: 2, minimal: 1, none: 0 }
  },
  {
    id: 2,
    title: "Read backend notes",
    goal: "Improve system design",
    description: "Review one module and write short notes.",
    status: "todo",
    completion_level: null,
    score_awarded: 0,
    generated_reason: "weekly",
    scoring_snapshot_json: { perfect: 5, normal: 3, minimal: 1, none: 0 }
  },
  {
    id: 3,
    title: "Sleep before midnight",
    goal: "Better sleep rhythm",
    description: "Phone away by 11:30 PM.",
    status: "done",
    completion_level: "normal",
    score_awarded: 2,
    generated_reason: "daily",
    scoring_snapshot_json: { perfect: 3, normal: 2, minimal: 1, none: 0 }
  },
  {
    id: 4,
    title: "Submit project checkpoint",
    goal: "Improve system design",
    description: "Prepare notes and submit the milestone update.",
    status: "todo",
    completion_level: null,
    score_awarded: 0,
    generated_reason: "once",
    schedule_date: "2026-05-04",
    scoring_snapshot_json: { perfect: 5, normal: 3, minimal: 1, none: 0 }
  }
];

export const mockProfile = {
  email: "player@lifelikegame.app",
  display_name: "Player One",
  timezone: "Asia/Kuala_Lumpur",
  current_value: 15,
  joined_at: "2026-04-01"
};

export const mockGoals = [
  {
    id: 1,
    title: "Build consistent fitness",
    start_date: "2026-04-01",
    target_date: "2026-06-30",
    current_value: "8 workouts",
    target_value: "40 workouts"
  },
  {
    id: 2,
    title: "Improve system design",
    start_date: "2026-04-10",
    target_date: "2026-05-30",
    current_value: "3 modules reviewed",
    target_value: "12 modules reviewed"
  }
];

export const mockRewards = [
  {
    id: 1,
    title: "Hotpot dinner",
    description: "Weekend meal after hitting the weekly target.",
    cost_points: 35,
    status: "available"
  },
  {
    id: 2,
    title: "One gaming session",
    description: "Two hours guilt-free after all daily tasks are done.",
    cost_points: 20,
    status: "redeemed"
  },
  {
    id: 3,
    title: "New notebook",
    description: "Buy a better notebook after a strong study week.",
    cost_points: 50,
    status: "available"
  }
];

export const mockLedgers = [
  {
    id: 1,
    event_at: "2026-04-29",
    delta: 3,
    entry_type: "earn",
    source_type: "checkin",
    description: "Morning workout completed"
  },
  {
    id: 2,
    event_at: "2026-04-29",
    delta: 2,
    entry_type: "earn",
    source_type: "checkin",
    description: "Sleep routine completed"
  },
  {
    id: 3,
    event_at: "2026-04-28",
    delta: -20,
    entry_type: "spend",
    source_type: "redemption",
    description: "Redeemed one gaming session"
  },
  {
    id: 4,
    event_at: "2026-04-27",
    delta: 30,
    entry_type: "earn",
    source_type: "manual",
    description: "Weekly bonus"
  }
];
