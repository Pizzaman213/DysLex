import '@tiptap/core';
import { Correction } from '../stores/editorStore';

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    correctionHighlight: {
      /**
       * Set corrections to display
       */
      setCorrections: (corrections: Correction[]) => ReturnType;
    };
    focusMode: {
      /**
       * Toggle focus mode
       */
      toggleFocusMode: () => ReturnType;
      /**
       * Set focus mode state
       */
      setFocusMode: (enabled: boolean) => ReturnType;
    };
  }
}
