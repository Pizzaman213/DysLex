import { useState, useCallback, useEffect, useRef } from 'react';

/**
 * Add basic punctuation to a speech-recognized phrase:
 * capitalize the first letter and append a period if no end punctuation exists.
 */
function addPunctuation(text: string): string {
  const trimmed = text.trim();
  if (!trimmed) return trimmed;
  const capitalized = trimmed.charAt(0).toUpperCase() + trimmed.slice(1);
  if (/[.!?]$/.test(capitalized)) return capitalized;
  return capitalized + '.';
}

interface UseVoiceInputOptions {
  language?: string;
  continuous?: boolean;
  onResult?: (transcript: string) => void;
  onError?: (error: Error) => void;
}

export function useVoiceInput(options: UseVoiceInputOptions = {}) {
  const { language = 'en-US', continuous = true, onResult, onError } = options;

  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimText, setInterimText] = useState('');
  const [isSupported, setIsSupported] = useState(false);

  const recognitionRef = useRef<any>(null);
  const finalizedRef = useRef('');
  // Accumulates finalized text across auto-restarts so it isn't lost
  // when the SpeechRecognition session resets on silence.
  const accumulatedRef = useRef('');
  const stoppingRef = useRef(false);
  const activeRef = useRef(false);

  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
      setIsSupported(true);
      const recognition = new SpeechRecognition();
      recognition.lang = language;
      recognition.continuous = continuous;
      recognition.interimResults = true;

      recognition.onresult = (event: any) => {
        const finalSegments: string[] = [];
        let sessionInterim = '';

        for (let i = 0; i < event.results.length; i++) {
          const result = event.results[i];
          if (result.isFinal) {
            finalSegments.push(result[0].transcript);
          } else {
            sessionInterim += result[0].transcript;
          }
        }

        // Apply punctuation to each finalized utterance
        const sessionFinal = finalSegments
          .map((seg) => addPunctuation(seg))
          .join(' ');

        // Update finalized text when new finals arrive.
        // Combine with accumulated text from previous auto-restart sessions
        // so earlier speech isn't lost when the API resets on silence.
        if (sessionFinal) {
          const full = accumulatedRef.current
            ? accumulatedRef.current.trimEnd() + ' ' + sessionFinal.trimStart()
            : sessionFinal;
          finalizedRef.current = full;
          onResult?.(full);
        }

        // Capitalize interim text so it looks right while speaking
        const displayInterim = sessionInterim.trim()
          ? sessionInterim.trimStart().charAt(0).toUpperCase() +
            sessionInterim.trimStart().slice(1)
          : sessionInterim;

        // Build displayed transcript: all finalized + current interim
        const displayed = (finalizedRef.current + ' ' + displayInterim).trim();
        setTranscript(displayed);
        setInterimText(displayInterim);
      };

      recognition.onerror = (event: any) => {
        // "no-speech" and "aborted" are normal when stopping — don't surface them
        if (event.error === 'no-speech' || event.error === 'aborted') {
          return;
        }
        const error = new Error(`Speech recognition error: ${event.error}`);
        onError?.(error);
        activeRef.current = false;
        setIsListening(false);
      };

      recognition.onend = () => {
        // Auto-restart in continuous mode (Speech API stops on silence).
        // Save accumulated finals so the next session can build on them.
        if (!stoppingRef.current && continuous) {
          accumulatedRef.current = finalizedRef.current;
          try {
            recognition.start();
          } catch {
            // Already running or other error — ignore
            activeRef.current = false;
            setIsListening(false);
          }
          return;
        }
        activeRef.current = false;
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }

    return () => {
      stoppingRef.current = true;
      activeRef.current = false;
      recognitionRef.current?.stop();
    };
  }, [language, continuous, onResult, onError]);

  const startListening = useCallback(() => {
    if (recognitionRef.current && !activeRef.current) {
      stoppingRef.current = false;
      activeRef.current = true;
      finalizedRef.current = '';
      accumulatedRef.current = '';
      setInterimText('');
      recognitionRef.current.start();
      setIsListening(true);
    }
  }, []);

  const stopListening = useCallback(() => {
    if (recognitionRef.current && activeRef.current) {
      stoppingRef.current = true;
      activeRef.current = false;
      recognitionRef.current.stop();
      setIsListening(false);
      setInterimText('');
      // Set transcript to final value (strip any lingering interim)
      setTranscript(finalizedRef.current.trim());
    }
  }, []);

  const resetTranscript = useCallback(() => {
    finalizedRef.current = '';
    accumulatedRef.current = '';
    setTranscript('');
    setInterimText('');
  }, []);

  return {
    isListening,
    transcript,
    interimText,
    isSupported,
    startListening,
    stopListening,
    resetTranscript,
  };
}

declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}
