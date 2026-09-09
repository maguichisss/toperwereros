import { useState, useCallback } from 'react';

export default function useToast() {
  const [toast, setToast] = useState(null);

  const notify = useCallback((message, type = 'error') => {
    setToast({ message, type });
  }, []);

  const clear = useCallback(() => setToast(null), []);

  return { toast, notify, clear };
}