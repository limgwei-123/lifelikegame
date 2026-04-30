import React from "react";

export function CompletionModal({ task, onClose, onComplete }) {
  if (!task) return null;

  const levels = Object.entries(task.scoring_snapshot_json || { done: 1 });

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal" role="dialog" aria-modal="true" aria-labelledby="complete-title">
        <div className="modal-header">
          <div>
            <p className="eyebrow">Complete Task</p>
            <h3 id="complete-title">{task.title}</h3>
          </div>
          <button className="icon-button" onClick={onClose} type="button" aria-label="Close">
            x
          </button>
        </div>
        <div className="level-list">
          {levels.map(([level, points]) => (
            <button
              className="level-button"
              key={level}
              onClick={() => onComplete(level)}
              type="button"
            >
              <span>{level}</span>
              <strong>+{points}</strong>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
