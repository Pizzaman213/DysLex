import type { PageType } from '../types';

/** 1 CSS-inch at 96 dpi */
export const PAGE_MARGIN = 96;

interface PageDimension {
  width: number;
  height: number;
}

/** Page dimensions in pixels at 96 dpi */
export const PAGE_DIMENSIONS: Record<PageType, PageDimension> = {
  letter: { width: 816, height: 1056 },
  a4:     { width: 794, height: 1123 },
  legal:  { width: 816, height: 1344 },
  a5:     { width: 559, height: 794  },
  wide:   { width: 1056, height: 816 },
};

export function getContentWidth(pageType: PageType): number {
  return PAGE_DIMENSIONS[pageType].width - 2 * PAGE_MARGIN;
}

export function getContentHeight(pageType: PageType): number {
  return PAGE_DIMENSIONS[pageType].height - 2 * PAGE_MARGIN;
}
