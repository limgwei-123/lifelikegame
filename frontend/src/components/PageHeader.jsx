import React from "react";

export function PageHeader({ eyebrow, title, children }) {
  return (
    <header className="page-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        {title ? <h2>{title}</h2> : null}
      </div>
      {children ? <div className="header-actions">{children}</div> : null}
    </header>
  );
}
