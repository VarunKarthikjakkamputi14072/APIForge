"use client";

import { useEffect, useState } from "react";
import { MOCK_API_KEY } from "./mock";

const STORAGE_KEY = "apiforge.api_key";
const CREATED_KEY = "apiforge.api_key.created";

export function useApiKey() {
  const [apiKey, setApiKeyState] = useState<string>("");
  const [createdAt, setCreatedAt] = useState<string>("");
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    const created = window.localStorage.getItem(CREATED_KEY);
    if (stored) {
      setApiKeyState(stored);
      setCreatedAt(created ?? new Date().toISOString());
    } else {
      const now = new Date().toISOString();
      setApiKeyState(MOCK_API_KEY);
      setCreatedAt(now);
    }
    setHydrated(true);
  }, []);

  const setApiKey = (next: string) => {
    if (next) {
      const created = new Date().toISOString();
      window.localStorage.setItem(STORAGE_KEY, next);
      window.localStorage.setItem(CREATED_KEY, created);
      setApiKeyState(next);
      setCreatedAt(created);
    } else {
      window.localStorage.removeItem(STORAGE_KEY);
      window.localStorage.removeItem(CREATED_KEY);
      setApiKeyState(MOCK_API_KEY);
      setCreatedAt(new Date().toISOString());
    }
  };

  return { apiKey, createdAt, setApiKey, hydrated };
}

export function maskKey(value: string): string {
  if (!value) return "";
  if (value.length <= 12) return value.replace(/.(?=.{4})/g, "•");
  const head = value.slice(0, 6);
  const tail = value.slice(-4);
  return `${head}${"•".repeat(Math.max(8, value.length - 10))}${tail}`;
}
