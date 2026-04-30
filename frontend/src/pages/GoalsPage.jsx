import React, { useState } from "react";
import { CardMenu } from "../components/CardMenu.jsx";
import { CreateSheet } from "../components/CreateSheet.jsx";
import { Field } from "../components/Field.jsx";
import { PageHeader } from "../components/PageHeader.jsx";

export function GoalsPage({ goals, onDelete, onSave }) {
  const [isCreating, setIsCreating] = useState(false);
  const [editingGoal, setEditingGoal] = useState(null);

  const openCreate = () => {
    setEditingGoal(null);
    setIsCreating(true);
  };

  const openEdit = (goal) => {
    setEditingGoal(goal);
    setIsCreating(true);
  };

  const saveGoal = async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    await onSave(editingGoal, data);
    setIsCreating(false);
  };

  return (
    <>
      <PageHeader eyebrow="Goals" title="">
        <button className="fab-button" onClick={openCreate} type="button" aria-label="Create goal">
          +
        </button>
      </PageHeader>
      <section className="single-panel-layout">
        <div className="panel">
          <div className="section-title compact">
            <h3>Goal list</h3>
          </div>
          <div className="card-list">
            {goals.map((goal) => (
              <article className="plain-card editable-card" key={goal.id} onClick={() => openEdit(goal)}>
                <div className="card-title-bar">
                  <h4>{goal.title}</h4>
                  <CardMenu label="Goal actions" onDelete={() => onDelete(goal.id)} />
                </div>
                <p>{goal.current_value} / {goal.target_value}</p>
                <div className="date-row">
                  <span>{goal.start_date}</span>
                  <span>{goal.target_date}</span>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <CreateSheet
        eyebrow="Goals"
        title={editingGoal ? "Edit Goal" : "Create Goal"}
        open={isCreating}
        onClose={() => setIsCreating(false)}
      >
        <form className="form-grid" onSubmit={saveGoal}>
          <Field label="Title">
            <input defaultValue={editingGoal?.title ?? ""} name="title" placeholder="Build consistent fitness" />
          </Field>
          <Field label="Start date">
            <input defaultValue={editingGoal?.start_date ?? ""} name="start_date" type="date" />
          </Field>
          <Field label="Target date">
            <input defaultValue={editingGoal?.target_date ?? ""} name="target_date" type="date" />
          </Field>
          <Field label="Current value">
            <input defaultValue={editingGoal?.current_value ?? ""} name="current_value" placeholder="8 workouts" />
          </Field>
          <Field label="Target value">
            <input defaultValue={editingGoal?.target_value ?? ""} name="target_value" placeholder="40 workouts" />
          </Field>
          <button className="primary-button" type="submit">Save preview</button>
        </form>
      </CreateSheet>
    </>
  );
}
