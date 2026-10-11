const copy = (value) => JSON.parse(JSON.stringify(value));

function requireDraft(value) {
  if (!value || typeof value.draft_id !== "string" || !value.draft_id || !value.plan) {
    throw new Error("A saved AI draft is required. Generate a new plan.");
  }
}

export function createAiDraftFlow({ saveRevision, confirmDraft }) {
  let draft = null;
  let plan = null;
  let savedInputs = new Set();
  let pending = null;

  return {
    setDraft(value) {
      if (pending) throw new Error("AI draft is being saved.");
      requireDraft(value);
      draft = copy(value);
      plan = copy(value.plan);
      savedInputs = new Set([JSON.stringify(plan)]);
    },
    markEdited(value) {
      if (pending) throw new Error("AI draft is being saved.");
      plan = copy(value);
    },
    confirm() {
      if (pending) return pending;
      pending = Promise.resolve().then(async () => {
        requireDraft(draft);
        const inputKey = JSON.stringify(plan);
        if (!savedInputs.has(inputKey)) {
          const revised = await saveRevision(draft.draft_id, copy(plan));
          requireDraft(revised);
          draft = copy(revised);
          plan = copy(revised.plan);
          // Both the submitted edit and its canonical response identify this saved revision.
          savedInputs = new Set([inputKey, JSON.stringify(plan)]);
        }
        const result = await confirmDraft(draft.draft_id);
        draft = null;
        plan = null;
        savedInputs.clear();
        return result;
      }).finally(() => { pending = null; });
      return pending;
    }
  };
}

export async function refreshAfterAiConfirmation(refresh, reportError) {
  try {
    await refresh();
  } catch (error) {
    reportError(`Plan created, but dashboard refresh failed: ${error.message}`);
  }
}
