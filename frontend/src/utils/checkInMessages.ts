/**
 * Check-In Messages Database
 *
 * Empathetic messages shown when frustration is detected.
 * Each message is supportive, actionable, and non-condescending.
 */

export interface CheckInMessage {
  primary: string;
  suggestion?: string;
  actions?: Array<{ id: string; label: string }>;
}

const MESSAGES: Record<string, CheckInMessage[]> = {
  rapid_deletion: [
    {
      primary: "Noticing a lot of backspacing. This part might feel tricky.",
      suggestion: "Remember: first drafts don't need to be perfect.",
      actions: [
        { id: 'continue', label: "I'm Good" }
      ]
    },
    {
      primary: "You're working hard on getting this right.",
      suggestion: "Sometimes stepping away for a minute helps.",
      actions: [
        { id: 'take_break', label: 'Take a Break' },
        { id: 'continue', label: 'Keep Writing' }
      ]
    },
    {
      primary: "That's a lot of editing. You're being thorough.",
      suggestion: "It's okay to leave rough spots and come back later.",
      actions: [
        { id: 'continue', label: 'Thanks' }
      ]
    }
  ],

  long_pause: [
    {
      primary: "Stuck on what to say next?",
      suggestion: "Try speaking your thoughts out loud, or move to a different section.",
      actions: [
        { id: 'voice_mode', label: 'Switch to Voice' },
        { id: 'continue', label: 'Keep Thinking' }
      ]
    },
    {
      primary: "Taking your time is okay.",
      suggestion: "Sometimes the best ideas come when you're not forcing them.",
      actions: [
        { id: 'continue', label: 'Thanks' }
      ]
    },
    {
      primary: "Need a moment to think? That's completely normal.",
      suggestion: "Some writers find it helps to write about something else first.",
      actions: [
        { id: 'continue', label: "I'm Okay" }
      ]
    }
  ],

  short_burst: [
    {
      primary: "Having trouble getting into a flow?",
      suggestion: "Try writing without worrying about mistakes first.",
      actions: [
        { id: 'continue', label: "I'll Keep Trying" }
      ]
    },
    {
      primary: "Writing in short bursts is still writing.",
      suggestion: "Every word counts. You're making progress.",
      actions: [
        { id: 'continue', label: 'Thanks' }
      ]
    },
    {
      primary: "Finding your rhythm takes time.",
      suggestion: "Some sections flow easier than others — that's normal.",
      actions: [
        { id: 'voice_mode', label: 'Try Voice Mode' },
        { id: 'continue', label: 'Keep Going' }
      ]
    }
  ],

  cursor_thrash: [
    {
      primary: "Jumping around a lot. That's okay!",
      suggestion: "If you're stuck, try writing the part that feels easiest first.",
      actions: [
        { id: 'continue', label: 'Thanks' }
      ]
    },
    {
      primary: "Non-linear writing is a valid approach.",
      suggestion: "Your brain might be organizing ideas in the background.",
      actions: [
        { id: 'continue', label: 'Good to Know' }
      ]
    },
    {
      primary: "Looking for the right spot to write?",
      suggestion: "Sometimes it helps to outline your thoughts first.",
      actions: [
        { id: 'continue', label: "I'm Okay" }
      ]
    }
  ],

  mixed: [
    {
      primary: "This section seems challenging. You're doing great.",
      suggestion: "The writing process isn't linear. Take your time.",
      actions: [
        { id: 'take_break', label: 'Take a Break' },
        { id: 'continue', label: "I'm Okay" }
      ]
    },
    {
      primary: "Writing can be hard. You're putting in the effort.",
      suggestion: "Every writer struggles sometimes. You're not alone.",
      actions: [
        { id: 'voice_mode', label: 'Switch to Voice' },
        { id: 'continue', label: 'Keep Writing' }
      ]
    },
    {
      primary: "Noticing some friction in your writing flow.",
      suggestion: "That's normal. Sometimes the ideas need time to develop.",
      actions: [
        { id: 'continue', label: 'Thanks' }
      ]
    },
    {
      primary: "You're working through a tough part.",
      suggestion: "Remember: progress over perfection.",
      actions: [
        { id: 'take_break', label: 'Pause for a Moment' },
        { id: 'continue', label: 'Keep Going' }
      ]
    }
  ]
};

/**
 * Select an appropriate message based on detected frustration signals.
 *
 * @param signalTypes - Array of detected signal types
 * @returns A check-in message with primary text, suggestion, and actions
 */
export function selectMessage(signalTypes: string[]): CheckInMessage {
  // If single signal, use specific message for that type
  if (signalTypes.length === 1) {
    const messages = MESSAGES[signalTypes[0]] || MESSAGES.mixed;
    return messages[Math.floor(Math.random() * messages.length)];
  }

  // If multiple signals detected, use mixed/general messages
  const messages = MESSAGES.mixed;
  return messages[Math.floor(Math.random() * messages.length)];
}
