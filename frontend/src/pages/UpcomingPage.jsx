import React, { useMemo } from "react";
import { PageHeader } from "../components/PageHeader.jsx";

export function UpcomingPage({ tasks }) {
  const upcomingTasks = useMemo(() => {
    return tasks
      .filter((task) => task.generated_reason === "once")
      .sort((left, right) => {
        return (left.schedule_date ?? "").localeCompare(right.schedule_date ?? "");
      });
  }, [tasks]);

  return (
    <>
      <PageHeader eyebrow="Upcoming" title="Upcoming Dates" />

      <section className="single-panel-layout">
        <div className="panel">
          <div className="section-title compact">
            <h3>Once tasks</h3>
            <span className="pill">{upcomingTasks.length} scheduled</span>
          </div>
          <div className="card-list">
            {upcomingTasks.length === 0 ? (
              <p className="empty-text">No once dates scheduled yet.</p>
            ) : null}
            {upcomingTasks.map((task) => (
              <article className="plain-card upcoming-card" key={task.id}>
                <div>
                  <h4>{task.title}</h4>
                  <p>{task.description}</p>
                  <span className="goal-link">{task.goal}</span>
                </div>
                <strong>{task.schedule_date || "No date set"}</strong>
              </article>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
