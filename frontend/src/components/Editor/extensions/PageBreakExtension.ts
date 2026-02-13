import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import type { EditorView } from '@tiptap/pm/view';

/** Default fallbacks (A4 at 96 dpi with 96px margin) */
const DEFAULT_CONTENT_HEIGHT = 931;
const DEFAULT_MARGIN = 96;

/** Read page dimensions from CSS custom properties on the container */
function readDimensions(container: HTMLElement) {
  const cs = getComputedStyle(container);
  const contentHeight =
    parseFloat(cs.getPropertyValue('--page-content-height')) || DEFAULT_CONTENT_HEIGHT;
  const pagePad =
    parseFloat(cs.getPropertyValue('--page-margin')) || DEFAULT_MARGIN;
  const pageGap = 2 * pagePad + 32;
  return { contentHeight, pagePad, pageGap };
}

/**
 * Suppress ProseMirror's internal DOMObserver while executing a callback.
 * PM watches its DOM for mutations and re-renders from state, stripping any
 * external style/attribute changes we make. By stopping its observer during
 * our DOM writes, we prevent PM from reverting our page-break margins.
 */
function withSuppressedPMObserver(view: EditorView, fn: () => void) {
  const domObs = (view as any).domObserver;
  if (domObs) {
    domObs.stop();
    try {
      fn();
    } finally {
      domObs.start();
    }
  } else {
    fn();
  }
}

export const PageBreakExtension = Extension.create({
  name: 'pageBreaks',

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey('pageBreaks'),
        view(editorView) {
          let rafId: number | null = null;
          let lastSize = 0;
          const pageCards: HTMLElement[] = [];
          const pageGaps: HTMLElement[] = [];
          const pageNumberEls: HTMLElement[] = [];
          const runningHeaderEls: HTMLElement[] = [];
          let containerEl: HTMLElement | null = null;
          let styleObserver: MutationObserver | null = null;

          // Track last-seen page dimensions to detect real pageType changes
          let lastContentHeight = 0;
          let lastPagePad = 0;

          /** Walk up from ProseMirror DOM to find .draft-page / .editor-page */
          function findContainer(el: HTMLElement | null): HTMLElement | null {
            while (el) {
              if (
                el.classList.contains('draft-page') ||
                el.classList.contains('editor-page')
              ) {
                return el;
              }
              el = el.parentElement;
            }
            return null;
          }

          /** Check if an ancestor has .view-continuous class */
          function isContinuousMode(el: HTMLElement | null): boolean {
            while (el) {
              if (el.classList.contains('view-continuous')) return true;
              el = el.parentElement;
            }
            return false;
          }

          function cleanupPageOverlays(container: HTMLElement) {
            pageCards.forEach((card) => card.remove());
            pageCards.length = 0;
            pageGaps.forEach((gap) => gap.remove());
            pageGaps.length = 0;
            pageNumberEls.forEach((el) => el.remove());
            pageNumberEls.length = 0;
            runningHeaderEls.forEach((el) => el.remove());
            runningHeaderEls.length = 0;
            container.style.minHeight = '';
          }

          function recalc() {
            const dom = editorView.dom as HTMLElement;
            const blocks = Array.from(dom.children) as HTMLElement[];

            const container = findContainer(dom);
            if (!container) return;
            containerEl = container;

            // In continuous mode, clean up any existing page overlays and bail out
            if (isContinuousMode(container)) {
              withSuppressedPMObserver(editorView, () => {
                for (const block of blocks) {
                  if (block.dataset.pageBreak) {
                    block.style.marginTop = '';
                    delete block.dataset.pageBreak;
                  }
                  block.classList.remove('page-break-before');
                }
              });
              cleanupPageOverlays(container);
              return;
            }

            const { contentHeight, pagePad, pageGap } = readDimensions(container);

            // Update tracked dimensions
            lastContentHeight = contentHeight;
            lastPagePad = pagePad;

            // Suppress PM's DOMObserver for ALL our DOM mutations
            // (clearing old margins + applying new ones)
            withSuppressedPMObserver(editorView, () => {
              // ── Phase 1: clear previous page-break margins ──
              for (const block of blocks) {
                if (block.dataset.pageBreak) {
                  block.style.marginTop = '';
                  delete block.dataset.pageBreak;
                }
                block.classList.remove('page-break-before');
              }

              // Force synchronous layout after clearing margins
              void dom.offsetHeight;

              // ── Phase 2: read natural positions ──
              const domRect = dom.getBoundingClientRect();
              const entries = blocks.map((el) => {
                const rect = el.getBoundingClientRect();
                return {
                  el,
                  top: rect.top - domRect.top,
                  height: rect.height,
                };
              });

              // ── Phase 3: push overflowing elements to next page ──
              let shift = 0;
              let nextBreak = contentHeight;

              for (const entry of entries) {
                if (entry.height === 0) continue;

                const adjustedTop = entry.top + shift;
                const adjustedBottom = adjustedTop + entry.height;

                if (adjustedBottom > nextBreak) {
                  const margin = nextBreak - adjustedTop + pageGap;
                  entry.el.style.marginTop = `${margin}px`;
                  entry.el.dataset.pageBreak = '1';
                  entry.el.classList.add('page-break-before');
                  shift += margin;

                  nextBreak = adjustedTop + margin + contentHeight;
                }

                const currentBottom = entry.top + shift + entry.height;
                while (currentBottom > nextBreak) {
                  nextBreak += contentHeight + pageGap;
                }
              }

              // ── Phase 3b: re-measure actual positions after margins ──
              void dom.offsetHeight;
              const totalPMHeight = dom.scrollHeight;
              const freshDomRect = dom.getBoundingClientRect();

              const measuredBreaks: { contentEnd: number; nextStart: number }[] = [];
              let prevBlock: HTMLElement | null = null;
              for (const block of blocks) {
                if (block.dataset.pageBreak) {
                  const r = block.getBoundingClientRect();
                  const nextStart = r.top - freshDomRect.top;
                  let contentEnd = nextStart;
                  if (prevBlock) {
                    contentEnd = prevBlock.getBoundingClientRect().bottom - freshDomRect.top;
                  }
                  measuredBreaks.push({ contentEnd, nextStart });
                }
                if (block.offsetHeight > 0) {
                  prevBlock = block;
                }
              }

              // Build page ranges from measured positions
              const pageRanges: { start: number; end: number }[] = [];
              let pageStart = 0;
              for (const brk of measuredBreaks) {
                pageRanges.push({ start: pageStart, end: brk.contentEnd });
                pageStart = brk.nextStart;
              }
              // Close last page
              pageRanges.push({
                start: pageStart,
                end: Math.max(totalPMHeight, pageStart + contentHeight),
              });

              // ── Phase 4: create / update page-card overlays ──
              const containerRect = container.getBoundingClientRect();
              const pmTop = freshDomRect.top - containerRect.top;

              // Resize card pool
              while (pageCards.length > pageRanges.length) {
                pageCards.pop()?.remove();
              }
              while (pageCards.length < pageRanges.length) {
                const card = document.createElement('div');
                card.className = 'page-card';
                container.appendChild(card);
                pageCards.push(card);
              }

              // Position each card
              const fullPageHeight = pmTop + contentHeight + pmTop;

              for (let i = 0; i < pageRanges.length; i++) {
                const { start, end } = pageRanges[i];
                const card = pageCards[i];
                const isFirst = i === 0;

                let cardTop: number;
                let cardBottom: number;

                if (isFirst) {
                  cardTop = 0;
                  cardBottom = Math.max(pmTop + end + pmTop, fullPageHeight);
                } else {
                  cardTop = pmTop + start - pagePad;
                  cardBottom = Math.max(
                    pmTop + end + pmTop,
                    cardTop + fullPageHeight,
                  );
                }

                card.style.top = `${cardTop}px`;
                card.style.height = `${cardBottom - cardTop}px`;
              }

              // ── Phase 4b: create / update gap divs between pages ──
              const gapCount = Math.max(0, pageRanges.length - 1);

              while (pageGaps.length > gapCount) {
                pageGaps.pop()?.remove();
              }
              while (pageGaps.length < gapCount) {
                const gap = document.createElement('div');
                gap.className = 'page-gap';
                container.appendChild(gap);
                pageGaps.push(gap);
              }

              for (let i = 0; i < gapCount; i++) {
                const card1Bottom = parseFloat(pageCards[i].style.top) + parseFloat(pageCards[i].style.height);
                const card2Top = parseFloat(pageCards[i + 1].style.top);
                pageGaps[i].style.top = `${card1Bottom}px`;
                pageGaps[i].style.height = `${card2Top - card1Bottom}px`;
              }

              // Make sure the container is tall enough for all cards
              const lastCard = pageCards[pageCards.length - 1];
              if (lastCard) {
                const needed =
                  parseFloat(lastCard.style.top) +
                  parseFloat(lastCard.style.height);
                container.style.minHeight = `${needed}px`;
              }

              // ── Phase 5: page numbers ──
              const showPageNumbers = container.dataset.pageNumbers === 'true';

              if (showPageNumbers) {
                // Resize pool
                while (pageNumberEls.length > pageRanges.length) {
                  pageNumberEls.pop()?.remove();
                }
                while (pageNumberEls.length < pageRanges.length) {
                  const span = document.createElement('span');
                  span.className = 'page-number';
                  pageNumberEls.push(span);
                }

                for (let i = 0; i < pageRanges.length; i++) {
                  const span = pageNumberEls[i];
                  span.textContent = String(i + 1);
                  // Append to corresponding page card
                  if (span.parentElement !== pageCards[i]) {
                    pageCards[i].appendChild(span);
                  }
                }
              } else {
                // Remove all page number elements
                pageNumberEls.forEach((el) => el.remove());
                pageNumberEls.length = 0;
              }

              // ── Phase 6: running headers ──
              const headerType = container.dataset.runningHeaderType || '';
              const headerLastName = container.dataset.headerLastName || '';
              const headerTitle = container.dataset.headerTitle || '';

              if (headerType && showPageNumbers) {
                // Resize pool
                while (runningHeaderEls.length > pageRanges.length) {
                  runningHeaderEls.pop()?.remove();
                }
                while (runningHeaderEls.length < pageRanges.length) {
                  const el = document.createElement('span');
                  el.className = 'running-header';
                  runningHeaderEls.push(el);
                }

                for (let i = 0; i < pageRanges.length; i++) {
                  const el = runningHeaderEls[i];
                  const pageNum = i + 1;

                  if (headerType === 'lastname-page') {
                    // MLA: "LastName PageNumber" top-right
                    el.textContent = headerLastName ? `${headerLastName} ${pageNum}` : String(pageNum);
                    el.className = 'running-header running-header--right';
                  } else if (headerType === 'shortened-title') {
                    // APA: "SHORTENED TITLE" left, page number right
                    el.innerHTML = '';
                    const leftSpan = document.createElement('span');
                    leftSpan.className = 'running-header__left';
                    leftSpan.textContent = headerTitle ? headerTitle.toUpperCase() : '';
                    const rightSpan = document.createElement('span');
                    rightSpan.className = 'running-header__right';
                    rightSpan.textContent = String(pageNum);
                    el.appendChild(leftSpan);
                    el.appendChild(rightSpan);
                    el.className = 'running-header running-header--split';
                  }
                  // page-only: already handled by page numbers

                  if (el.parentElement !== pageCards[i]) {
                    pageCards[i].appendChild(el);
                  }
                }

                // Hide page number elements when running header includes them
                if (headerType === 'lastname-page' || headerType === 'shortened-title') {
                  pageNumberEls.forEach((el) => { el.style.display = 'none'; });
                }
              } else {
                // Remove running headers
                runningHeaderEls.forEach((el) => el.remove());
                runningHeaderEls.length = 0;
                // Restore page number visibility
                pageNumberEls.forEach((el) => { el.style.display = ''; });
              }
            }); // end withSuppressedPMObserver
          }

          function schedule() {
            if (rafId) cancelAnimationFrame(rafId);
            rafId = requestAnimationFrame(() => {
              rafId = null;
              recalc();
            });
          }

          // Run on first mount
          schedule();

          // Second pass after a short delay to catch any late layout shifts
          setTimeout(schedule, 150);

          // Window resize replaces ResizeObserver to avoid feedback loops.
          const onWindowResize = () => schedule();
          window.addEventListener('resize', onWindowResize);

          // Watch container style attribute for pageType changes.
          // Compare actual dimension values to ignore our own minHeight updates.
          const initContainer = findContainer(editorView.dom as HTMLElement);
          if (initContainer) {
            containerEl = initContainer;
            styleObserver = new MutationObserver((mutations) => {
              const hasDataChange = mutations.some(
                (m) => m.attributeName === 'data-page-numbers' ||
                       m.attributeName === 'data-running-header-type' ||
                       m.attributeName === 'data-header-last-name' ||
                       m.attributeName === 'data-header-title'
              );
              if (hasDataChange) {
                schedule();
                return;
              }
              const { contentHeight, pagePad } = readDimensions(initContainer);
              if (contentHeight !== lastContentHeight || pagePad !== lastPagePad) {
                schedule();
              }
            });
            styleObserver.observe(initContainer, {
              attributes: true,
              attributeFilter: ['style', 'data-page-numbers', 'data-running-header-type', 'data-header-last-name', 'data-header-title'],
            });
          }

          return {
            update(view) {
              const size = view.state.doc.content.size;
              if (size !== lastSize) {
                lastSize = size;
                schedule();
              }
            },
            destroy() {
              if (rafId) cancelAnimationFrame(rafId);
              window.removeEventListener('resize', onWindowResize);
              styleObserver?.disconnect();
              withSuppressedPMObserver(editorView, () => {
                const blocks = Array.from(
                  editorView.dom.children,
                ) as HTMLElement[];
                for (const block of blocks) {
                  block.style.marginTop = '';
                  block.classList.remove('page-break-before');
                }
              });
              pageNumberEls.forEach((el) => el.remove());
              pageNumberEls.length = 0;
              runningHeaderEls.forEach((el) => el.remove());
              runningHeaderEls.length = 0;
              pageCards.forEach((card) => card.remove());
              pageCards.length = 0;
              pageGaps.forEach((gap) => gap.remove());
              pageGaps.length = 0;
              if (containerEl) {
                containerEl.style.minHeight = '';
                containerEl = null;
              }
            },
          };
        },
      }),
    ];
  },
});
