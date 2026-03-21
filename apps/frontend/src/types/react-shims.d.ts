declare module 'react' {
  export type ReactNode = unknown;
  export type PropsWithChildren<P = unknown> = P & { children?: ReactNode };
  const React: {
    StrictMode: unknown;
  };
  export default React;
}

declare module 'react-dom/client' {
  export function createRoot(container: Element | DocumentFragment): {
    render(children: unknown): void;
  };
}

declare namespace JSX {
  interface IntrinsicAttributes {
    key?: string | number;
  }

  interface IntrinsicElements {
    [elemName: string]: any;
  }
}


declare module 'react/jsx-runtime' {
  export const Fragment: unknown;
  export function jsx(type: unknown, props: unknown, key?: unknown): unknown;
  export function jsxs(type: unknown, props: unknown, key?: unknown): unknown;
}
