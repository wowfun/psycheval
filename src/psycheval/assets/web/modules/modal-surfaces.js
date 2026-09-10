const modalOpeners = new WeakMap();
const modalBodyClasses = new WeakMap();
const modalClosers = new WeakMap();
const boundModals = new WeakSet();
const suspendedModals = new WeakMap();

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
  modalClosers.get(root)?.();
  modalClosers.delete(root);
  return true;
}

function openModalSurface(root, options = {}) {
  if (!root) return false;
  document.querySelectorAll('[aria-modal="true"]').forEach(candidate => {
    const otherRoot = candidate.closest("[data-view-save-dialog],[data-admin-login-dialog]") || candidate;
    if (otherRoot === root || otherRoot.hidden) return;
    if (otherRoot.matches(".action-form-overlay")) {
      suspendedModals.set(root, { root: otherRoot, focus: document.activeElement });
      otherRoot.hidden = true;
      return;
    }
    hideModalSurface(otherRoot);
    modalOpeners.delete(otherRoot);
    modalBodyClasses.delete(otherRoot);
  });
  modalOpeners.set(root, options.opener || document.activeElement || null);
  modalBodyClasses.set(root, options.bodyClass || "");
  modalClosers.set(root, options.onClose);
  if (!boundModals.has(root)) {
    boundModals.add(root);
    root.addEventListener("keydown", event => {
      if (root.hidden || event.key !== "Tab") return;
      const controls = [...root.querySelectorAll(':is(button, input, select, textarea, a[href], [tabindex="0"]):not(:disabled)')]
        .filter(node => !node.closest("[hidden]"));
      const first = controls[0], last = controls.at(-1);
      if (!first) { event.preventDefault(); return; }
      if (event.shiftKey && (document.activeElement === first || !root.contains(document.activeElement))) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first.focus();
      }
    });
  }
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
  const suspended = suspendedModals.get(root);
  suspendedModals.delete(root);
  if (suspended?.root.isConnected) {
    suspended.root.hidden = false;
    if (options.restoreFocus !== false) focusSoon(suspended.focus);
  } else if (options.restoreFocus !== false) focusSoon(opener);
  return true;
}

export { closeModalSurface, focusSoon, openModalSurface };
