import type { PropsWithChildren } from 'react';

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="app-shell">
      <header className="hero">
        <p className="eyebrow">Prediction Markets Intelligence Platform</p>
        <h1>market-trading-bot</h1>
        <p className="hero-copy">
          Initial monorepo scaffold for a modular web platform focused on analysis,
          paper trading, and future automation workflows.
        </p>
      </header>
      <main>{children}</main>
    </div>
  );
}
