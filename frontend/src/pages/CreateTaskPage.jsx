import React, { useState } from "react";
import { CardMenu } from "../components/CardMenu.jsx";
import { CreateSheet } from "../components/CreateSheet.jsx";
import { Field } from "../components/Field.jsx";
import { PageHeader } from "../components/PageHeader.jsx";

const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const monthDays = Array.from({ length: 31 }, (_, index) => index + 1);

export function TasksPage({ goals, onDelete, onSave, scoringSchemes, tasks }) {
  const [isCreating, setIsCreating] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [scheduleType, setScheduleType] = useState("weekly");
  const [monthlyDay, setMonthlyDay] = useState(1);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const openCreate = () => {
    setEditingTask(null);
    setScheduleType("weekly");
    setMonthlyDay(1);
    setError("");
    setIsCreating(true);
  };

  const openEdit = (task) => {
    setEditingTask(task);
    setScheduleType(task.generated_reason);
    setMonthlyDay(task.schedule_value_json?.day ?? 1);
    setError("");
    setIsCreating(true);
  };

  const saveTask = async (event) => {
    event.preventDefault();
    if (saving) return;

    const formData = new FormData(event.currentTarget);
    const data = Object.fromEntries(formData);
    const weeklyDays = formData.getAll("weekly_days");

    setSaving(true);
    setError("");
    try {
      await onSave(editingTask, {
        ...data,
        schedule_type: scheduleType,
        monthly_day: monthlyDay,
        weekly_days: weeklyDays
      });
      setIsCreating(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <PageHeader eyebrow="Tasks" title="">
        <button className="fab-button" onClick={openCreate} type="button" aria-label="Add task">
          +
        </button>
      </PageHeader>

      <section className="single-panel-layout">
        <div className="panel">
          <div className="section-title compact">
            <h3>Task list</h3>
            <span className="pill">{tasks.length} active</span>
          </div>
          <div className="task-list">
            {tasks.length === 0 ? (
              <p className="empty-text">No task templates yet.</p>
            ) : null}
            {tasks.map((task) => (
              <article
                className="task-card editable-card"
                key={task.id}
                onClick={() => openEdit(task)}
              >
                <div className="task-main">
                  <div>
                    <div className="card-title-bar">
                      <h4>{task.title}</h4>
                      <CardMenu label="Task actions" onDelete={() => onDelete(task.id)} />
                    </div>
                    <span className="pill muted">{task.schedule_label}</span>
                    <p>{task.description}</p>
                    <span className="goal-link">{task.goal}</span>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <CreateSheet
        eyebrow="Tasks"
        title={editingTask ? "Edit Task" : "Add Task"}
        open={isCreating}
        onClose={() => setIsCreating(false)}
      >
        <form className="form-grid two-column" onSubmit={saveTask}>
          {error ? <p className="empty-text">{error}</p> : null}
          <Field label="Task title">
            <input defaultValue={editingTask?.title ?? ""} name="title" placeholder="Morning workout" />
          </Field>
          <Field label="Goal">
            <select defaultValue={editingTask?.goal_id ?? goals[0]?.id ?? ""} name="goal_id" required>
              {goals.map((goal) => (
                <option key={goal.id} value={goal.id}>{goal.title}</option>
              ))}
            </select>
          </Field>
          <Field label="Description">
            <textarea defaultValue={editingTask?.description ?? ""} name="description" placeholder="What should the task contain?" rows="4" />
          </Field>
          <Field label="Scoring scheme">
            <select defaultValue={editingTask?.scoring_scheme_id ?? scoringSchemes[0]?.id ?? ""} name="scoring_scheme_id">
              <option value="">Default</option>
              {scoringSchemes.map((scheme) => (
                <option key={scheme.id} value={scheme.id}>{scheme.title}</option>
              ))}
            </select>
          </Field>
          <Field label="Schedule type">
            <select value={scheduleType} onChange={(event) => setScheduleType(event.target.value)}>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="once">Once</option>
            </select>
          </Field>

          {scheduleType === "weekly" ? (
            <div className="day-picker">
              {days.map((day, index) => (
                <label key={day}>
                  <input
                    defaultChecked={(editingTask?.schedule_value_json?.days ?? [0, 2, 4]).includes(index)}
                    name="weekly_days"
                    type="checkbox"
                    value={index}
                  />
                  <span>{day.slice(0, 3)}</span>
                </label>
              ))}
            </div>
          ) : null}

          {scheduleType === "monthly" ? (
            <div className="month-day-field">
              <span>Repeat on day</span>
              <div className="month-day-scroll" role="listbox" aria-label="Monthly day">
                {monthDays.map((day) => (
                  <button
                    className={monthlyDay === day ? "month-day active" : "month-day"}
                    key={day}
                    onClick={() => setMonthlyDay(day)}
                    type="button"
                  >
                    {day}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          <Field label={scheduleType === "once" ? "Date" : "Start date"}>
            <input defaultValue={editingTask?.schedule_date ?? ""} name="schedule_date" type="date" />
          </Field>

          {scheduleType !== "once" ? (
            <Field label="End date">
              <input defaultValue={editingTask?.schedule_end_date ?? ""} name="end_date" type="date" />
            </Field>
          ) : null}

          <div className="form-actions">
            <button className="secondary-button" type="button">Reset</button>
            <button className="primary-button" disabled={saving} type="submit">
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </form>
      </CreateSheet>
    </>
  );
}
