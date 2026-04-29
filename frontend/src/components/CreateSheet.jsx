import React from "react";

export function CreateSheet({ title, eyebrow, open, onClose, children }) {
  if (!open) return null;

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal create-sheet" role="dialog" aria-modal="true" aria-labelledby="create-sheet-title">
        <div className="modal-header">
          <div>
            <p className="eyebrow">{eyebrow}</p>
            <h3 id="create-sheet-title">{title}</h3>
          </div>
          <button className="icon-button" onClick={onClose} type="button" aria-label="Close">
            x
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}
