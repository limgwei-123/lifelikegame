import React, { useMemo, useState } from "react";
import { generateAiPlan } from "../api/aiPlannerApi.js";
import { CreateSheet } from "../components/CreateSheet.jsx";
import { Field } from "../components/Field.jsx";
import { PageHeader } from "../components/PageHeader.jsx";
import { formatScheduleLabel } from "../utils/scheduleLabels.js";

const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function normalizeTask(task = {}) {
  const scheduleType = task.schedule_type === "daily" ? "daily" : "weekly";
  const scheduleValue = task.schedule_value_json ?? {};

  return {
    title: task.title ?? "",
    description: task.description ?? "",
    schedule_type: scheduleType,
    schedule_value_json:
      scheduleType === "weekly"
        ? { days: Array.isArray(scheduleValue.days) && scheduleValue.days.length ? scheduleValue.days : [0, 2, 4] }
        : {}
  };
}

function normalizePlan(plan) {
  return {
    goal_title: plan?.goal_title ?? "",
    tasks: (plan?.tasks?.length ? plan.tasks : [normalizeTask()]).map(normalizeTask)
  };
}

export function AiPlannerPage({ onConfirmPlan }) {
  const [prompt, setPrompt] = useState("");
  const [conversationHistory, setConversationHistory] = useState([]);
  const [messages, setMessages] = useState([]);
  const [readyPlan, setReadyPlan] = useState(null);
  const [editablePlan, setEditablePlan] = useState(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const planTaskCount = useMemo(() => editablePlan?.tasks?.length ?? 0, [editablePlan]);

  const submitPrompt = async (event) => {
    event.preventDefault();
    const userPrompt = prompt.trim();
    if (!userPrompt || submitting) return;

    setSubmitting(true);
    setError("");
    setMessages((current) => [...current, { role: "user", content: userPrompt }]);
    setPrompt("");

    try {
      const response = await generateAiPlan({
        user_prompt: userPrompt,
        conversation_history: conversationHistory
      });

      setConversationHistory(response.conversation_history ?? []);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: response.message,
          questions: response.questions ?? [],
          status: response.status
        }
      ]);

      if (response.status === "plan_ready" && response.plan) {
        const nextPlan = normalizePlan(response.plan);
        setReadyPlan(nextPlan);
        setEditablePlan(nextPlan);
        setConfirmOpen(true);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const updateGoalTitle = (value) => {
    setEditablePlan((current) => ({ ...current, goal_title: value }));
  };

  const updateTask = (index, patch) => {
    setEditablePlan((current) => ({
      ...current,
      tasks: current.tasks.map((task, taskIndex) => (
        taskIndex === index ? normalizeTask({ ...task, ...patch }) : task
      ))
    }));
  };

  const updateTaskScheduleType = (index, scheduleType) => {
    updateTask(index, {
      schedule_type: scheduleType,
      schedule_value_json: scheduleType === "weekly" ? { days: [0, 2, 4] } : {}
    });
  };

  const toggleWeeklyDay = (taskIndex, dayIndex) => {
    setEditablePlan((current) => ({
      ...current,
      tasks: current.tasks.map((task, index) => {
        if (index !== taskIndex) return task;

        const currentDays = task.schedule_value_json?.days ?? [];
        const nextDays = currentDays.includes(dayIndex)
          ? currentDays.filter((day) => day !== dayIndex)
          : [...currentDays, dayIndex].sort((left, right) => left - right);

        return {
          ...task,
          schedule_value_json: { days: nextDays }
        };
      })
    }));
  };

  const addTask = () => {
    setEditablePlan((current) => ({
      ...current,
      tasks: [
        ...current.tasks,
        normalizeTask({
          title: "New task",
          description: "",
          schedule_type: "weekly",
          schedule_value_json: { days: [0, 2, 4] }
        })
      ]
    }));
  };

  const removeTask = (index) => {
    setEditablePlan((current) => ({
      ...current,
      tasks: current.tasks.filter((_, taskIndex) => taskIndex !== index)
    }));
  };

  const confirmPlan = async () => {
    if (!editablePlan || saving) return;

    const nextPlan = normalizePlan(editablePlan);
    if (!nextPlan.goal_title.trim()) {
      setError("Goal title is required.");
      return;
    }
    if (nextPlan.tasks.length === 0) {
      setError("At least one task is required.");
      return;
    }
    if (nextPlan.tasks.some((task) => !task.title.trim())) {
      setError("Every task needs a title.");
      return;
    }
    if (nextPlan.tasks.some((task) => task.schedule_type === "weekly" && task.schedule_value_json.days.length === 0)) {
      setError("Weekly tasks need at least one day selected.");
      return;
    }

    setSaving(true);
    setError("");
    try {
      await onConfirmPlan({
        ...nextPlan,
        goal_title: nextPlan.goal_title.trim(),
        tasks: nextPlan.tasks.map((task) => ({
          ...task,
          title: task.title.trim(),
          description: task.description?.trim() || null
        }))
      });
      setConfirmOpen(false);
      setReadyPlan(null);
      setEditablePlan(null);
      setMessages([]);
      setConversationHistory([]);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <PageHeader eyebrow="AI" title="Planner" />

      <section className="ai-planner-layout">
        <div className="panel ai-planner-panel">
          <div className="section-title compact">
            <div>
              <p className="eyebrow">Assistant</p>
              <h3>Plan builder</h3>
            </div>
            {readyPlan ? (
              <div className="header-actions">
                <span className="pill">Plan ready</span>
                <button className="secondary-button" onClick={() => setConfirmOpen(true)} type="button">
                  Review plan
                </button>
              </div>
            ) : null}
          </div>

          {error ? <p className="empty-text">{error}</p> : null}

          <div className="ai-chat-log" aria-live="polite">
            {messages.length === 0 ? (
              <p className="empty-text">Tell the planner your goal, constraints, and weekly availability.</p>
            ) : null}

            {messages.map((message, index) => (
              <article className={`ai-message ${message.role}`} key={`${message.role}-${index}`}>
                <strong>{message.role === "user" ? "You" : "AI Planner"}</strong>
                <p>{message.content}</p>
                {message.status === "plan_ready" ? <span className="pill">Plan ready</span> : null}
                {message.questions?.length ? (
                  <div className="ai-question-list">
                    {message.questions.map((question) => (
                      <span key={question}>{question}</span>
                    ))}
                  </div>
                ) : null}
              </article>
            ))}
          </div>

          <form className="ai-planner-form" onSubmit={submitPrompt}>
            <Field label="Message">
              <textarea
                name="prompt"
                onChange={(event) => setPrompt(event.target.value)}
                placeholder="I want to build a workout routine..."
                rows="4"
                value={prompt}
              />
            </Field>
            <button className="primary-button" disabled={submitting} type="submit">
              {submitting ? "Planning..." : "Send"}
            </button>
          </form>
        </div>
      </section>

      <CreateSheet
        eyebrow="AI Planner"
        title="Confirm plan"
        open={confirmOpen}
        onClose={() => {
          if (!saving) setConfirmOpen(false);
        }}
      >
        <div className="plan-preview">
          <div className="form-grid">
            <Field label="Goal title">
              <input
                onChange={(event) => updateGoalTitle(event.target.value)}
                placeholder="Build consistent fitness"
                value={editablePlan?.goal_title ?? ""}
              />
            </Field>
            <p className="empty-text">{planTaskCount} tasks will be created from this plan.</p>
          </div>

          <div className="task-list plan-edit-list">
            {editablePlan?.tasks?.map((task, index) => (
              <article className="task-card plan-edit-card" key={`plan-task-${index}`}>
                <div className="card-title-bar">
                  <div>
                    <p className="eyebrow">Task {index + 1}</p>
                    <h4>{task.title || "Untitled task"}</h4>
                  </div>
                  <button
                    className="danger-button"
                    disabled={saving || editablePlan.tasks.length <= 1}
                    onClick={() => removeTask(index)}
                    type="button"
                  >
                    Remove
                  </button>
                </div>

                <div className="form-grid two-column">
                  <Field label="Task title">
                    <input
                      onChange={(event) => updateTask(index, { title: event.target.value })}
                      value={task.title}
                    />
                  </Field>
                  <Field label="Schedule">
                    <select
                      onChange={(event) => updateTaskScheduleType(index, event.target.value)}
                      value={task.schedule_type}
                    >
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                    </select>
                  </Field>
                  <Field label="Description">
                    <textarea
                      onChange={(event) => updateTask(index, { description: event.target.value })}
                      rows="3"
                      value={task.description ?? ""}
                    />
                  </Field>

                  {task.schedule_type === "weekly" ? (
                    <div className="day-picker plan-day-picker">
                      {days.map((day, dayIndex) => (
                        <label key={day}>
                          <input
                            checked={task.schedule_value_json?.days?.includes(dayIndex) ?? false}
                            onChange={() => toggleWeeklyDay(index, dayIndex)}
                            type="checkbox"
                            value={dayIndex}
                          />
                          <span>{day.slice(0, 3)}</span>
                        </label>
                      ))}
                    </div>
                  ) : null}

                  <span className="pill muted">
                    {formatScheduleLabel(task.schedule_type, task.schedule_value_json)}
                  </span>
                </div>
              </article>
            ))}
          </div>

          <button className="secondary-button" disabled={saving} onClick={addTask} type="button">
            Add task
          </button>

          <div className="confirm-actions">
            <button className="secondary-button" disabled={saving} onClick={() => setConfirmOpen(false)} type="button">
              Cancel
            </button>
            <button className="primary-button" disabled={saving} onClick={confirmPlan} type="button">
              {saving ? "Saving..." : "Confirm"}
            </button>
          </div>
        </div>
      </CreateSheet>
    </>
  );
}
