// Thin wrapper around sonner's `toast` that enforces consistent auto-dismiss
// durations app-wide: success/info toasts clear after 5s, error toasts stay
// a bit longer (8s) since they usually carry more to read.
// Import `toast` from here instead of directly from 'sonner' so every call
// site gets this behavior without having to remember a `duration` option.
import { toast as sonnerToast, type ExternalToast } from 'sonner';

const SUCCESS_DURATION_MS = 5000;
const ERROR_DURATION_MS = 8000;

type ToastMessage = Parameters<typeof sonnerToast>[0];

function success(message: ToastMessage, opts?: ExternalToast) {
  return sonnerToast.success(message, { duration: SUCCESS_DURATION_MS, ...opts });
}

function error(message: ToastMessage, opts?: ExternalToast) {
  return sonnerToast.error(message, { duration: ERROR_DURATION_MS, ...opts });
}

function info(message: ToastMessage, opts?: ExternalToast) {
  return sonnerToast.info(message, { duration: SUCCESS_DURATION_MS, ...opts });
}

function warning(message: ToastMessage, opts?: ExternalToast) {
  return sonnerToast.warning(message, { duration: SUCCESS_DURATION_MS, ...opts });
}

export const toast = Object.assign(sonnerToast, {
  success,
  error,
  info,
  warning,
});
