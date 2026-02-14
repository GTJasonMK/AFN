interface ScheduleIdleTaskOptions {
  delay?: number;
  timeout?: number;
}

type WindowWithIdleCallback = Window & {
  requestIdleCallback?: (callback: IdleRequestCallback, options?: IdleRequestOptions) => number;
  cancelIdleCallback?: (handle: number) => void;
};

export const scheduleIdleTask = (
  task: () => void,
  options: ScheduleIdleTaskOptions = {}
): (() => void) => {
  const { delay = 0, timeout = 1800 } = options;

  if (typeof window === 'undefined') {
    task();
    return () => {};
  }

  const win = window as WindowWithIdleCallback;
  let timerId: number | null = null;
  let idleId: number | null = null;

  const runTask = () => {
    if (typeof win.requestIdleCallback === 'function') {
      idleId = win.requestIdleCallback(() => {
        idleId = null;
        task();
      }, { timeout });
      return;
    }

    timerId = window.setTimeout(() => {
      timerId = null;
      task();
    }, 32);
  };

  if (delay > 0) {
    timerId = window.setTimeout(() => {
      timerId = null;
      runTask();
    }, delay);
  } else {
    runTask();
  }

  return () => {
    if (timerId !== null) {
      window.clearTimeout(timerId);
      timerId = null;
    }

    if (idleId !== null && typeof win.cancelIdleCallback === 'function') {
      win.cancelIdleCallback(idleId);
      idleId = null;
    }
  };
};
