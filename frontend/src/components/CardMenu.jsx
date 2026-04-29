import React, { useState } from "react";

export function CardMenu({ label = "More actions", onDelete }) {
  const [open, setOpen] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const close = () => {
    setOpen(false);
    setConfirming(false);
  };

  return (
    <div className="card-menu" onClick={(event) => event.stopPropagation()}>
      <button
        className="menu-dot-button"
        onClick={() => setOpen((value) => !value)}
        type="button"
        aria-label={label}
      >
        <span aria-hidden="true" />
      </button>
      {open ? (
        <div className="card-menu-popover">
          {confirming ? (
            <>
              <p>Are you sure?</p>
              <div className="confirm-actions">
                <button className="secondary-button" onClick={close} type="button">Cancel</button>
                <button
                  className="danger-button"
                  onClick={() => {
                    onDelete();
                    close();
                  }}
                  type="button"
                >
                  Delete
                </button>
              </div>
            </>
          ) : (
            <button className="menu-delete-button" onClick={() => setConfirming(true)} type="button">
              Delete
            </button>
          )}
        </div>
      ) : null}
    </div>
  );
}
