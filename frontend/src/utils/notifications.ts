// Web Audio API & Browser Notification Utilities for Work Completed Announcements

let titleTimeout: any = null;

export function playWorkDoneChime() {
  try {
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();

    // Dual-tone chime: C5 (523.25 Hz) then G5 (783.99 Hz) with harmonic chime C6 (1046.5 Hz)
    const t0 = ctx.currentTime;
    
    // Note 1: C5
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(523.25, t0);
    gain1.gain.setValueAtTime(0.12, t0);
    gain1.gain.exponentialRampToValueAtTime(0.001, t0 + 0.35);
    osc1.connect(gain1);
    gain1.connect(ctx.destination);
    osc1.start(t0);
    osc1.stop(t0 + 0.35);

    // Note 2: G5 (resonant bell)
    const t1 = t0 + 0.12;
    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.type = 'sine';
    osc2.frequency.setValueAtTime(783.99, t1);
    gain2.gain.setValueAtTime(0.15, t1);
    gain2.gain.exponentialRampToValueAtTime(0.001, t1 + 0.65);
    osc2.connect(gain2);
    gain2.connect(ctx.destination);
    osc2.start(t1);
    osc2.stop(t1 + 0.65);

    // Note 3: Harmonic shimmer C6
    const t2 = t0 + 0.22;
    const osc3 = ctx.createOscillator();
    const gain3 = ctx.createGain();
    osc3.type = 'triangle';
    osc3.frequency.setValueAtTime(1046.5, t2);
    gain3.gain.setValueAtTime(0.06, t2);
    gain3.gain.exponentialRampToValueAtTime(0.0001, t2 + 0.7);
    osc3.connect(gain3);
    gain3.connect(ctx.destination);
    osc3.start(t2);
    osc3.stop(t2 + 0.7);
  } catch (err) {
    console.debug('Audio chime unable to play:', err);
  }
}

export function notifyTabTitle(message: string, durationMs: number = 8000) {
  if (typeof document === 'undefined') return;
  const originalTitle = 'AI Operations Agent - Enterprise Autonomous Copilot';
  if (titleTimeout) clearTimeout(titleTimeout);
  document.title = message;
  titleTimeout = setTimeout(() => {
    document.title = originalTitle;
  }, durationMs);
}

export async function sendDesktopNotification(title: string, body: string) {
  if (typeof window === 'undefined' || !('Notification' in window)) return;
  if (Notification.permission === 'granted') {
    try {
      new Notification(title, { body });
    } catch {
      // Ignore
    }
  } else if (Notification.permission !== 'denied') {
    try {
      const perm = await Notification.requestPermission();
      if (perm === 'granted') {
        new Notification(title, { body });
      }
    } catch {
      // Ignore
    }
  }
}
