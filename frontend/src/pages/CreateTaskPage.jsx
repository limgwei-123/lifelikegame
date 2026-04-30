import React, { useState } from "react";
import { CardMenu } from "../components/CardMenu.jsx";
import { CreateSheet } from "../components/CreateSheet.jsx";
import { Field } from "../components/Field.jsx";
import { PageHeader } from "../components/PageHeader.jsx";

const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const monthDays = Array.from({ length: 31 }, (_, index) => index + 1);

export function TasksPage({ tasks, setTasks }) {
  const [isCreating, setIsCreating] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [scheduleType, setScheduleType] = useState("weekly");
  const [monthlyDay, setMonthlyDay] = useState(1);

  const openCreate = () => {
    setEditingTask(null);
    setScheduleType("weekly");
    setIsCreating(true);
  };

  const openEdit = (task) => {
    setEditingTask(task);
    setScheduleType(task.generated_reason);
    setIsCreating(true);
  };

  const deleteTask = (taskId) => {
    setTasks((items) => items.filter((task) => task.id !== taskId));
  };

  const saveTask = (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    const nextTask = {
      title: data.title,
      goal: data.goal,
      description: data.description,
      generated_reason: scheduleType,
      schedule_date: scheduleType === "once" ? data.schedule_date : null,
      scoring_snapshot_json: editingTask?.scoring_snapshot_json ?? { done: 1, good: 2, perfect: 3 }
    };

    if (editingTask) {
      setTasks((items) =>
        items.map((task) => (task.id === editingTask.id ? { ...task, ...nextTask } : task))
      );
    } else {
      setTasks((items) => [
        ...items,
        {
          id: Date.now(),
          status: "todo",
          completion_level: null,
          score_awarded: 0,
          ...nextTask
        }
      ]);
    }
    setIsCreating(false);
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
                      <CardMenu label="Task actions" onDelete={() => deleteTask(task.id)} />
                    </div>
                    <span className="pill muted">{task.generated_reason} schedule</span>
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
          <Field label="Task title">
            <input defaultValue={editingTask?.title ?? ""} name="title" placeholder="Morning workout" />
          </Field>
          <Field label="Goal">
            <select defaultValue={editingTask?.goal ?? "Build consistent fitness"} name="goal">
              <option value="Build consistent fitness">Build consistent fitness</option>
              <option value="Improve system design">Improve system design</option>
              <option value="Better sleep rhythm">Better sleep rhythm</option>
            </select>
          </Field>
          <Field label="Description">
            <textarea defaultValue={editingTask?.description ?? ""} name="description" placeholder="What should the task contain?" rows="4" />
          </Field>
          <Field label="Scoring scheme">
            <select defaultValue="normal">
              <option value="normal">Normal: 3 / 2 / 1 / 0</option>
              <option value="deep-work">Deep work: 5 / 3 / 1 / 0</option>
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
                  <input defaultChecked={[0, 2, 4].includes(index)} type="checkbox" />
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
              <input type="date" />
            </Field>
          ) : null}

          <div className="form-actions">
            <button className="secondary-button" type="button">Reset</button>
            <button className="primary-button" type="submit">Save preview</button>
          </div>
        </form>
      </CreateSheet>
    </>
  );
}
