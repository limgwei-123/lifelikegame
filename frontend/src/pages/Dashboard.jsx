import React, { useMemo, useState } from "react";
import { CompletionModal } from "../components/CompletionModal.jsx";
import { MetricCard } from "../components/MetricCard.jsx";
import { PageHeader } from "../components/PageHeader.jsx";

export function Dashboard({ tasks, balance, onComplete }) {
  const [selectedTask, setSelectedTask] = useState(null);
  const [activeStatus, setActiveStatus] = useState("todo");
  const doneCount = tasks.filter((task) => task.status === "done").length;
  const todoTasks = tasks.filter((task) => task.status === "todo");
  const doneTasks = tasks.filter((task) => task.status === "done");
  const visibleTasks = activeStatus === "todo" ? todoTasks : doneTasks;
  const earnedToday = tasks.reduce((total, task) => total + task.score_awarded, 0);
  const progress = useMemo(
    () => (tasks.length ? Math.round((doneCount / tasks.length) * 100) : 0),
    [doneCount, tasks.length]
  );

  const closeModal = () => setSelectedTask(null);

  return (
    <>
      <PageHeader eyebrow="Today" title="Dashboard" />

      <section className="metrics-grid">
        <MetricCard label="Current balance" value={`${balance} pts`} detail="From point ledger records" />
        <MetricCard label="Earned today" value={`+${earnedToday} pts`} detail="Based on completed task instances" />
        <MetricCard label="Completion" value={`${progress}%`} detail={`${doneCount} of ${tasks.length} tasks done`} />
      </section>

      <section className="single-panel-layout">
        <div className="panel">
          <div className="section-title">
            <div>
              <p className="eyebrow">Task Instances</p>
              <h3>Today's list</h3>
            </div>
            <span className="pill">{new Date().toLocaleDateString()}</span>
          </div>

          <div className="reward-segmented" role="tablist" aria-label="Task instance status">
            <button
              className={activeStatus === "todo" ? "segment active" : "segment"}
              onClick={() => setActiveStatus("todo")}
              type="button"
            >
              <span>Todo</span>
              <b>{todoTasks.length}</b>
            </button>
            <button
              className={activeStatus === "done" ? "segment active" : "segment"}
              onClick={() => setActiveStatus("done")}
              type="button"
            >
              <span>Done</span>
              <b>{doneTasks.length}</b>
            </button>
          </div>

          <div className="task-list">
            {visibleTasks.length === 0 ? (
              <p className="empty-text">
                {activeStatus === "todo" ? "No task instances left for today." : "No completed task instances yet."}
              </p>
            ) : null}
            {visibleTasks.map((task) => (
              <article className={task.status === "done" ? "task-card done" : "task-card"} key={task.id}>
                <div className="task-main">
                  <div className="check-dot" aria-hidden="true">{task.status === "done" ? "✓" : ""}</div>
                  <div>
                    <div className="task-title-row">
                      <h4>{task.title}</h4>
                      <span className="pill muted">{task.generated_reason}</span>
                    </div>
                    <p>{task.description}</p>
                    <span className="goal-link">{task.goal}</span>
                  </div>
                </div>
                <div className="task-actions">
                  {task.status === "done" ? (
                    <span className="status-label">
                      {task.completion_level} · +{task.score_awarded} pts
                    </span>
                  ) : (
                    <button className="secondary-button" onClick={() => setSelectedTask(task)} type="button">
                      Mark done
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <CompletionModal
        task={selectedTask}
        onClose={closeModal}
        onComplete={(level) => {
          onComplete(selectedTask.id, level);
          closeModal();
        }}
      />
    </>
  );
}
