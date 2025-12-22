import { useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';

export const useSession = () => {
  const [sessionId, setSessionId] = useState(null);

  useEffect(() => {
    // 1. Check if we already have a session in LocalStorage
    let storedSession = localStorage.getItem('logistics_session_id');

    // 2. If not, generate a new UUID and save it
    if (!storedSession) {
      storedSession = uuidv4();
      localStorage.setItem('logistics_session_id', storedSession);
      console.log("New Session Created:", storedSession);
    } else {
      console.log("Restored Existing Session:", storedSession);
    }

    setSessionId(storedSession);
  }, []);

  return sessionId;
};