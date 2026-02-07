import { useState, useCallback, useEffect, useRef } from 'react';

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
  const stoppingRef = useRef(false);

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
        let sessionFinal = '';
        let sessionInterim = '';

        for (let i = 0; i < event.results.length; i++) {
          const result = event.results[i];
          if (result.isFinal) {
            sessionFinal += result[0].transcript;
          } else {
            sessionInterim += result[0].transcript;
          }
        }

        // Update finalized text when new finals arrive
        if (sessionFinal && sessionFinal !== finalizedRef.current) {
          finalizedRef.current = sessionFinal;
          onResult?.(sessionFinal);
        }

        // Build displayed transcript: all finalized + current interim
        const displayed = (finalizedRef.current + ' ' + sessionInterim).trim();
        setTranscript(displayed);
        setInterimText(sessionInterim);
      };

      recognition.onerror = (event: any) => {
        // "no-speech" and "aborted" are normal when stopping — don't surface them
        if (event.error === 'no-speech' || event.error === 'aborted') {
          return;
        }
        const error = new Error(`Speech recognition error: ${event.error}`);
        onError?.(error);
        setIsListening(false);
      };

      recognition.onend = () => {
        // Auto-restart in continuous mode (Speech API stops on silence)
        if (!stoppingRef.current && continuous) {
          try {
            recognition.start();
          } catch {
            // Already running or other error — ignore
            setIsListening(false);
          }
          return;
        }
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }

    return () => {
      stoppingRef.current = true;
      recognitionRef.current?.stop();
    };
  }, [language, continuous, onResult, onError]);

  const startListening = useCallback(() => {
    if (recognitionRef.current && !isListening) {
      stoppingRef.current = false;
      finalizedRef.current = '';
      setInterimText('');
      recognitionRef.current.start();
      setIsListening(true);
    }
  }, [isListening]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current && isListening) {
      stoppingRef.current = true;
      recognitionRef.current.stop();
      setIsListening(false);
      setInterimText('');
      // Set transcript to final value (strip any lingering interim)
      setTranscript(finalizedRef.current.trim());
    }
  }, [isListening]);

  const resetTranscript = useCallback(() => {
    finalizedRef.current = '';
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
