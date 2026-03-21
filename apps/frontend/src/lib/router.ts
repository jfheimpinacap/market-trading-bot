import { useSyncExternalStore } from 'react';

const NAVIGATION_EVENT = 'app:navigation';

function subscribe(onStoreChange: () => void) {
  window.addEventListener('popstate', onStoreChange);
  window.addEventListener(NAVIGATION_EVENT, onStoreChange as EventListener);

  return () => {
    window.removeEventListener('popstate', onStoreChange);
    window.removeEventListener(NAVIGATION_EVENT, onStoreChange as EventListener);
  };
}

function getSnapshot() {
  return window.location.pathname || '/';
}

function getServerSnapshot() {
  return '/';
}

export function usePathname() {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

export function navigate(path: string) {
  if (window.location.pathname === path) {
    return;
  }

  window.history.pushState({}, '', path);
  window.dispatchEvent(new Event(NAVIGATION_EVENT));
}
