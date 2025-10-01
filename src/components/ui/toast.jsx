import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FaCheckCircle, FaTimesCircle, FaInfoCircle } from 'react-icons/fa';

const ToastContext = createContext({ toast: () => {} });

let idCounter = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const remove = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(({ title, description, variant = 'info', duration = 3000 } = {}) => {
    const id = ++idCounter;
    setToasts((prev) => [...prev, { id, title, description, variant }]);
    if (duration > 0) {
      setTimeout(() => remove(id), duration);
    }
    return id;
  }, [remove]);

  const value = useMemo(() => ({ toast, remove }), [toast, remove]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed top-4 right-4 z-[9999] space-y-2 w-[90vw] max-w-sm">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: -10, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.98 }}
              transition={{ duration: 0.2 }}
              className={
                `glass-card p-4 rounded-lg shadow-lg border flex items-start gap-3 ` +
                (t.variant === 'success' ? 'border-green-200 bg-green-50' : t.variant === 'error' ? 'border-red-200 bg-red-50' : 'border-blue-200 bg-blue-50')
              }
            >
              <div className="pt-0.5">
                {t.variant === 'success' ? (
                  <FaCheckCircle className="text-green-600" />
                ) : t.variant === 'error' ? (
                  <FaTimesCircle className="text-red-600" />
                ) : (
                  <FaInfoCircle className="text-blue-600" />
                )}
              </div>
              <div className="flex-1">
                {t.title ? <div className="font-semibold mb-0.5">{t.title}</div> : null}
                {t.description ? <div className="text-sm opacity-90">{t.description}</div> : null}
              </div>
              <button
                onClick={() => remove(t.id)}
                className="text-sm text-muted-foreground hover:opacity-70"
              >
                Dismiss
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  return ctx;
}


