// A filter stays in its table's DOM for event ownership, but paints in the top layer.
function bindTableFilterPopup(menu, reset) {
  const panel = menu.querySelector('.filter-menu');
  const trigger = menu.querySelector('summary');
  if (!panel.showPopover) { panel.removeAttribute("popover"); return; }
  let cleanup = () => {};
  const close = () => { menu.open = false; reset(); };
  const position = () => {
    if (!menu.isConnected || menu.closest('[hidden]')) { close(); return; }
    const rect = trigger.getBoundingClientRect();
    const viewport = menu.closest('.table-wrap')?.getBoundingClientRect();
    if (rect.bottom < 0 || rect.top > innerHeight || viewport && (rect.right < viewport.left || rect.left > viewport.right)) { close(); return; }
    const below = innerHeight - rect.bottom - 14;
    const above = rect.top - 14;
    const upwards = below < 180 && above > below;
    panel.style.maxHeight = `${Math.max(80, Math.min(320, upwards ? above : below))}px`;
    panel.style.maxWidth = `${Math.max(160, innerWidth - 16)}px`;
    const bounds = panel.getBoundingClientRect();
    panel.style.left = `${Math.max(8, Math.min(rect.left, innerWidth - bounds.width - 8))}px`;
    panel.style.top = `${Math.max(8, upwards ? rect.top - bounds.height - 6 : rect.bottom + 6)}px`;
  };
  menu.addEventListener('toggle', () => {
    cleanup();
    if (!menu.isConnected || !menu.open) { if (panel.matches(':popover-open')) panel.hidePopover(); return; }
    panel.showPopover();
    position();
    const outside = event => { if (!menu.contains(event.target)) close(); };
    const scroll = event => { if (!panel.contains(event.target)) position(); };
    const observer = new MutationObserver(() => { if (!menu.isConnected) { cleanup(); if (panel.matches(':popover-open')) panel.hidePopover(); } });
    observer.observe(document.body, { childList: true, subtree: true });
    document.addEventListener('pointerdown', outside, true);
    document.addEventListener('scroll', scroll, true);
    window.addEventListener('resize', position);
    cleanup = () => {
      observer.disconnect();
      document.removeEventListener('pointerdown', outside, true);
      document.removeEventListener('scroll', scroll, true);
      window.removeEventListener('resize', position);
    };
  });
  panel.addEventListener('toggle', () => { if (!panel.matches(':popover-open') && menu.open) close(); });
}

export { bindTableFilterPopup };
