// Status: partial-real
declare module 'reveal.js' {
  export type RevealOptions = {
    embedded?: boolean;
    controls?: boolean;
    progress?: boolean;
    center?: boolean;
    hash?: boolean;
    width?: number;
    height?: number;
    margin?: number;
  };

  export default class Reveal {
    constructor(element?: Element | null, options?: RevealOptions);
    initialize(): Promise<void>;
    destroy(): void;
    sync(): void;
  }
}
