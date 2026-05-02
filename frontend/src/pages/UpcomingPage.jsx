import React, { useEffect, useMemo, useState } from "react";
import { listTaskInstancesByMonth } from "../api/taskInstancesApi.js";
import { PageHeader } from "../components/PageHeader.jsx";
import { formatSimpleScheduleLabel } from "../utils/scheduleLabels.js";

const weekDays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function toDateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getMonthGrid(monthDate) {
  const year = monthDate.getFullYear();
  const month = monthDate.getMonth();
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const leadingDays = (firstDay.getDay() + 6) % 7;
  const days = [];

  for (let index = 0; index < leadingDays; index += 1) {
    days.push(null);
  }

  for (let day = 1; day <= lastDay.getDate(); day += 1) {
    days.push(new Date(year, month, day));
  }

  while (days.length % 7 !== 0) {
    days.push(null);
  }

  return days;
}

function mapInstance(instance, tasks, goals, taskSchedules) {
  const task = tasks.find((item) => item.id === instance.task_id);
  const goal = goals.find((item) => item.id === task?.goal_id);
  const schedule = taskSchedules.find((item) => item.id === instance.task_schedule_id);

  return {
    ...instance,
    title: task?.title ?? `Task #${instance.task_id}`,
    description: task?.description ?? "",
    goal: goal?.title ?? "Goal",
    schedule_label: formatSimpleScheduleLabel(
      schedule?.schedule_type ?? instance.generated_reason,
    )
  };
}

export function UpcomingPage({ goals, tasks, taskSchedules }) {
  const [visibleMonth, setVisibleMonth] = useState(() => {
    const today = new Date();
    return new Date(today.getFullYear(), today.getMonth(), 1);
  });
  const [monthInstances, setMonthInstances] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const todayKey = toDateKey(new Date());
  const monthLabel = visibleMonth.toLocaleDateString(undefined, {
    month: "long",
    year: "numeric"
  });

  const visibleDays = useMemo(() => getMonthGrid(visibleMonth), [visibleMonth]);

  useEffect(() => {
    let cancelled = false;

    const loadMonthInstances = async () => {
      setLoading(true);
      setError("");
      try {
        const results = await listTaskInstancesByMonth(visibleMonth.getFullYear(), visibleMonth.getMonth() + 1);
        if (!cancelled) {
          setMonthInstances(results);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    loadMonthInstances();

    return () => {
      cancelled = true;
    };
  }, [visibleMonth]);

  const calendarItems = useMemo(() => {
    const monthPrefix = `${visibleMonth.getFullYear()}-${String(visibleMonth.getMonth() + 1).padStart(2, "0")}`;

    return monthInstances
      .filter((instance) => instance.status === "todo" && instance.date_instance?.startsWith(monthPrefix))
      .map((instance) => mapInstance(instance, tasks, goals, taskSchedules));
  }, [goals, monthInstances, taskSchedules, tasks, visibleMonth]);

  const tasksByDate = useMemo(() => {
    return calendarItems.reduce((grouped, task) => {
      if (!task.date_instance) return grouped;
      grouped[task.date_instance] = [...(grouped[task.date_instance] ?? []), task];
      return grouped;
    }, {});
  }, [calendarItems]);

  const visibleTaskCount = visibleDays.reduce((total, day) => {
    if (!day) return total;
    return total + (tasksByDate[toDateKey(day)]?.length ?? 0);
  }, 0);

  const shiftMonth = (offset) => {
    setVisibleMonth((current) => new Date(current.getFullYear(), current.getMonth() + offset, 1));
  };

  return (
    <>
      <PageHeader eyebrow="Upcoming" title={monthLabel}>
        <button className="icon-button" onClick={() => shiftMonth(-1)} type="button" aria-label="Previous month">
          ‹
        </button>
        <button className="secondary-button" onClick={() => setVisibleMonth(new Date())} type="button">
          This month
        </button>
        <button className="icon-button" onClick={() => shiftMonth(1)} type="button" aria-label="Next month">
          ›
        </button>
      </PageHeader>

      <section className="single-panel-layout">
        <div className="panel calendar-panel">
          <div className="section-title compact">
            <h3>Todo calendar</h3>
            <span className="pill">{loading ? "Loading..." : `${visibleTaskCount} this month`}</span>
          </div>

          {error ? <p className="empty-text">{error}</p> : null}

          <div className="calendar-grid" role="grid" aria-label={`${monthLabel} todo calendar`}>
            {weekDays.map((day) => (
              <div className="calendar-weekday" key={day}>
                {day}
              </div>
            ))}

            {visibleDays.map((day, index) => {
              if (!day) {
                return <div className="calendar-day is-empty" key={`empty-${index}`} />;
              }

              const dateKey = toDateKey(day);
              const dayTasks = tasksByDate[dateKey] ?? [];

              return (
                <div className={dateKey === todayKey ? "calendar-day is-today" : "calendar-day"} key={dateKey}>
                  <div className="calendar-day-header">
                    <span>{day.getDate()}</span>
                    {dayTasks.length ? <b>{dayTasks.length}</b> : null}
                  </div>
                  <div className="calendar-todos">
                    {dayTasks.map((task) => (
                      <article className="calendar-todo" key={task.id}>
                        <strong>{task.title}</strong>
                        <span>{task.goal}</span>
                        <em>{task.schedule_label}</em>
                      </article>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {!loading && calendarItems.length === 0 ? <p className="empty-text">No todo instances for this month.</p> : null}
        </div>
      </section>
    </>
  );
}
