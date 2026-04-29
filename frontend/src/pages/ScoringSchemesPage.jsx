import React, { useMemo, useState } from "react";
import { CardMenu } from "../components/CardMenu.jsx";
import { CreateSheet } from "../components/CreateSheet.jsx";
import { Field } from "../components/Field.jsx";
import { PageHeader } from "../components/PageHeader.jsx";

const defaultSchemes = [
  { title: "normal", levels_json: { done: 1, good: 2, perfect: 3 } },
  { title: "deep-work", levels_json: { done: 2, good: 4, perfect: 6 } }
];

export function ScoringSchemesPage() {
  const [isCreating, setIsCreating] = useState(false);
  const [editingScheme, setEditingScheme] = useState(null);
  const [schemes, setSchemes] = useState(defaultSchemes);
  const [levels, setLevels] = useState([
    { id: 1, name: "done", points: 1 },
    { id: 2, name: "good", points: 2 },
    { id: 3, name: "perfect", points: 3 }
  ]);

  const canDelete = levels.length > 1;
  const levelsPreview = useMemo(() => {
    return levels.reduce((data, level) => {
      if (level.name.trim()) data[level.name.trim()] = Number(level.points) || 0;
      return data;
    }, {});
  }, [levels]);

  const updateLevel = (id, field, value) => {
    setLevels((items) =>
      items.map((item) => (item.id === id ? { ...item, [field]: value } : item))
    );
  };

  const addLevel = () => {
    setLevels((items) => [
      ...items,
      { id: Date.now(), name: "custom", points: 1 }
    ]);
  };

  const deleteLevel = (id) => {
    if (!canDelete) return;
    setLevels((items) => items.filter((item) => item.id !== id));
  };

  const openCreate = () => {
    setEditingScheme(null);
    setLevels([
      { id: 1, name: "done", points: 1 },
      { id: 2, name: "good", points: 2 },
      { id: 3, name: "perfect", points: 3 }
    ]);
    setIsCreating(true);
  };

  const openEdit = (scheme) => {
    setEditingScheme(scheme);
    setLevels(
      Object.entries(scheme.levels_json).map(([name, points], index) => ({
        id: index + 1,
        name,
        points
      }))
    );
    setIsCreating(true);
  };

  const deleteScheme = (title) => {
    setSchemes((items) => items.filter((scheme) => scheme.title !== title));
  };

  const saveScheme = (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    const nextScheme = {
      title: data.title || "normal",
      levels_json: levelsPreview
    };
    if (editingScheme) {
      setSchemes((items) =>
        items.map((scheme) => (scheme.title === editingScheme.title ? nextScheme : scheme))
      );
    } else {
      setSchemes((items) => [...items, nextScheme]);
    }
    setIsCreating(false);
  };

  return (
    <>
      <PageHeader eyebrow="Scoring" title="">
        <button className="fab-button" onClick={openCreate} type="button" aria-label="Create scoring scheme">
          +
        </button>
      </PageHeader>
      <section className="single-panel-layout">
        <div className="panel">
          <div className="section-title compact">
            <h3>Scheme list</h3>
          </div>
          <div className="card-list">
            {schemes.map((scheme) => (
              <article className="plain-card editable-card" key={scheme.title} onClick={() => openEdit(scheme)}>
                <div className="card-title-bar">
                  <h4>{scheme.title}</h4>
                  <CardMenu label="Scoring scheme actions" onDelete={() => deleteScheme(scheme.title)} />
                </div>
                <div className="scheme-row">
                  {Object.entries(scheme.levels_json).map(([level, value]) => (
                    <span key={level}>{level}: {value}</span>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <CreateSheet
        eyebrow="Scoring"
        title={editingScheme ? "Edit Scheme" : "Create Scheme"}
        open={isCreating}
        onClose={() => setIsCreating(false)}
      >
        <form className="form-grid" onSubmit={saveScheme}>
          <Field label="Title">
            <input defaultValue={editingScheme?.title ?? "normal"} name="title" />
          </Field>
          <div className="completion-level-editor">
            <div className="editor-heading">
              <span>Completion levels</span>
            </div>
            {levels.map((level) => (
              <div className="level-editor-row" key={level.id}>
                <Field label="Level name">
                  <input
                    value={level.name}
                    onChange={(event) => updateLevel(level.id, "name", event.target.value)}
                  />
                </Field>
                <Field label="Points">
                  <input
                    min="0"
                    type="number"
                    value={level.points}
                    onChange={(event) => updateLevel(level.id, "points", event.target.value)}
                  />
                </Field>
                <button
                  className="danger-button"
                  disabled={!canDelete}
                  onClick={() => deleteLevel(level.id)}
                  type="button"
                >
                  Delete
                </button>
              </div>
            ))}
            <button className="add-level-button" onClick={addLevel} type="button" aria-label="Add completion level">
              +
            </button>
            <div className="levels-preview">
              {Object.entries(levelsPreview).map(([level, points]) => (
                <span key={level}>{level}: {points}</span>
              ))}
            </div>
          </div>
          <button className="primary-button" type="submit">Save preview</button>
        </form>
      </CreateSheet>
    </>
  );
}
