const modalOpeners = new WeakMap();
const modalBodyClasses = new WeakMap();

function focusSoon(target) {
  if (!target || typeof target.focus !== "function") return;
  const apply = () => target.focus();
  if (typeof requestAnimationFrame === "function") requestAnimationFrame(apply);
  else apply();
}

function hideModalSurface(root) {
  if (!root || root.hidden) return false;
  root.hidden = true;
  const bodyClass = modalBodyClasses.get(root);
  if (bodyClass) document.body.classList.remove(bodyClass);
  return true;
}

function openModalSurface(root, options = {}) {
  if (!root) return false;
  document.querySelectorAll('[aria-modal="true"]').forEach(candidate => {
    const otherRoot = candidate.closest("[data-source-manager],[data-report-manager],[data-view-save-dialog]") || candidate;
    if (otherRoot === root) return;
    hideModalSurface(otherRoot);
    modalOpeners.delete(otherRoot);
    modalBodyClasses.delete(otherRoot);
  });
  modalOpeners.set(root, options.opener || document.activeElement || null);
  modalBodyClasses.set(root, options.bodyClass || "");
  root.hidden = false;
  if (options.bodyClass) document.body.classList.add(options.bodyClass);
  focusSoon(options.focusTarget || null);
  return true;
}

function closeModalSurface(root, options = {}) {
  if (!hideModalSurface(root)) return false;
  const opener = modalOpeners.get(root);
  modalOpeners.delete(root);
  modalBodyClasses.delete(root);
  if (options.restoreFocus !== false) focusSoon(opener);
  return true;
}

export { closeModalSurface, focusSoon, openModalSurface };
