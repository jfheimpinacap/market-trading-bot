declare module 'react' {
  export type ReactNode = unknown;
  export type PropsWithChildren<P = unknown> = P & { children?: ReactNode };
  export type MouseEvent<T = Element> = {
    preventDefault(): void;
    defaultPrevented: boolean;
    metaKey: boolean;
    ctrlKey: boolean;
    shiftKey: boolean;
    altKey: boolean;
    currentTarget: T;
  };
  export type Dispatch<S> = (value: S | ((prevState: S) => S)) => void;
  export type SetStateAction<S> = S | ((prevState: S) => S);
  export type Context<T> = {
    Provider(props: { value: T; children?: ReactNode }): JSX.Element;
  };
  export function createContext<T>(defaultValue: T): Context<T>;
  export function useContext<T>(context: Context<T>): T;
  export function useState<S>(initialState: S): [S, Dispatch<S>];
  export function useEffect(effect: () => void | (() => void), deps?: unknown[]): void;
  export function useCallback<T extends (...args: any[]) => any>(callback: T, deps: unknown[]): T;
  export function useSyncExternalStore<T>(
    subscribe: (onStoreChange: () => void) => () => void,
    getSnapshot: () => T,
    getServerSnapshot?: () => T,
  ): T;
  export const StrictMode: (props: { children?: ReactNode }) => JSX.Element;
  const React: {
    StrictMode: typeof StrictMode;
  };
  export default React;
}

declare module 'react-dom/client' {
  export function createRoot(container: Element | DocumentFragment): {
    render(children: unknown): void;
  };
}

declare namespace JSX {
  interface Element {}

  interface IntrinsicAttributes {
    key?: string | number;
    children?: any;
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
