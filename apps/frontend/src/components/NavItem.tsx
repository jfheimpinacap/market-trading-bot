import type { MouseEvent } from 'react';
import { navigate } from '../lib/router';

type NavItemProps = {
  label: string;
  path: string;
  active: boolean;
};

export function NavItem({ label, path, active }: NavItemProps) {
  const className = active ? 'nav-item nav-item--active' : 'nav-item';

  function handleClick(event: MouseEvent<HTMLAnchorElement>) {
    if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }

    event.preventDefault();
    navigate(path);
  }

  return (
    <a className={className} href={path} onClick={handleClick} aria-current={active ? 'page' : undefined}>
      <span>{label}</span>
    </a>
  );
}
